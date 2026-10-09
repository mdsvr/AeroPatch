"""Training data preparation (doc 09).

    uv run python training/prepare_dataset.py mine        # advisories -> training/data/fix_pairs.jsonl
    uv run python training/prepare_dataset.py spotcheck   # 20 random pairs re-applied, byte-exact
    uv run python training/prepare_dataset.py general     # SWE-Gym, SWE-smith -> training/data/general_pairs.jsonl
    uv run python training/prepare_dataset.py build --student-run <run id>
                                                          # -> train.jsonl, val.jsonl, leakage.md, training/stats.md

`mine` lists the reviewed pip advisories published before CUTOFF, keeps those whose one fix commit
changes exactly one non-test Python file by at most 60 lines, and turns each fix into the
assistant message the model is trained to write: RATIONALE plus SEARCH/REPLACE blocks (doc 09 §6).
A pair is kept only if that message, parsed and applied by the real `aeropatch.agent.edits`,
turns the pre-fix file into the post-fix file byte for byte. `general` does the same for ordinary
bug fixes from two public datasets.

`build` renders every pair with the functions the loop uses (`get_context`, `prompts`), applies
the filters of doc 09 §7 in order, adds the repair turns of the student run
(`inject_cwe.py --student`) and writes one example per line:
    {"messages": [system, user, (assistant, user)...], "target": <the assistant message to learn>, ...}
Only `target` is trained on. An assistant message inside `messages` is a failed edit of the student.

`mine` needs a GitHub token (GITHUB_TOKEN, or a logged-in `gh`). API answers are cached under
training/data/cache/, so a second run costs nothing and a stopped run resumes.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import itertools
import json
import keyword
import os
import random
import re
import subprocess
import tempfile
import warnings
from collections import Counter
from functools import lru_cache
from pathlib import Path

import httpx

from aeropatch import bench
from aeropatch.agent import edits, gates, prompts
from aeropatch.config import ROOT, RUNS_DIR, SCENARIOS_DIR
from aeropatch.contracts import Edit, Failure, Finding, Task
from aeropatch.sandbox import junit
from aeropatch.tools import context

DATA = ROOT / "training" / "data"  # gitignored: the script is published, the data is not (doc 09 §2)
CACHE = DATA / "cache"
PAIRS = DATA / "fix_pairs.jsonl"
GENERAL = DATA / "general_pairs.jsonl"
SYNTHETIC = ROOT / "training" / "synthetic"  # written by inject_cwe.py
STATS = ROOT / "training" / "stats.md"  # counts only, so it is published; leakage.md quotes code and is not

# Training CVEs are published before this date; Tier B's advisories start on 2026-03-16 (doc 09 §9).
CUTOFF = "2026-01-01"
# Repo split (doc 09 §9): the projects behind the Tier B scenarios. No pair from an advisory that
# names one of them, as a repository or as a package, is kept. tests/test_prepare_dataset.py
# checks this list against the scenarios.
EXCLUDED = {"mako", "mistune", "sqlparse", "microdot", "geopy", "flask-httpauth", "pyjwt", "hpack", "pyasn1"}
MAX_CHANGED_LINES = 60
COMMIT_RE = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/commit/([0-9a-f]{7,40})")
DOC_RE = re.compile(r"(^|/)(docs?/|changes|changelog|news|history|release|readme|authors)|\.(md|rst|txt)$", re.IGNORECASE)


def excluded(*names: str) -> bool:
    """True when a repository ("owner/name") or package name belongs to a benchmark project."""
    return any(re.sub(r"[._]", "-", n.rsplit("/", 1)[-1].lower()) in EXCLUDED for n in names)


def is_test(path: str) -> bool:
    return any(part.startswith(("test", "conftest")) or part.endswith("_test.py") for part in path.lower().split("/"))


def is_doc(path: str) -> bool:
    return not path.endswith(".py") and bool(DOC_RE.search(path))


# --- fix commit -> SEARCH/REPLACE target (doc 09 §6) ---

@lru_cache(maxsize=4)
def opcodes(pre: str, post: str) -> list[tuple[str, int, int, int, int]]:
    """The line diff of two files. Only the lines between the first and the last change are
    compared: SequenceMatcher took minutes on a file of thousands of lines, most of them equal."""
    a, b = pre.split("\n"), post.split("\n")
    short = min(len(a), len(b))
    head = next((i for i in range(short) if a[i] != b[i]), short)
    tail = next((i for i in range(short - head) if a[-1 - i] != b[-1 - i]), short - head)
    middle = difflib.SequenceMatcher(None, a[head:len(a) - tail], b[head:len(b) - tail], autojunk=False).get_opcodes()
    ops = [("equal", 0, head, 0, head), *((tag, i1 + head, i2 + head, j1 + head, j2 + head) for tag, i1, i2, j1, j2 in middle),
           ("equal", len(a) - tail, len(a), len(b) - tail, len(b))]
    return [op for op in ops if op[2] > op[1] or op[4] > op[3]]


def to_edits(pre: str, post: str, path: str, up: int = 1, down: int = 1) -> list[Edit] | None:
    """One block per changed region, with `up` and `down` or more unchanged lines above and below.

    With context a block starts and ends on an unchanged, non-blank line, because
    `edits.apply_one` trims blank lines off both ends of SEARCH and REPLACE. It grows until its
    SEARCH text occurs once in the file. Returns None when a block cannot be made unique.
    """
    a, b = pre.split("\n"), post.split("\n")
    rows: list[tuple[str | None, str | None]] = []  # the two files side by side: (old line, new line)
    for tag, i1, i2, j1, j2 in opcodes(pre, post):
        if tag == "equal":
            rows += [(line, line) for line in a[i1:i2]]
        else:
            rows += [(line, None) for line in a[i1:i2]] + [(None, line) for line in b[j1:j2]]

    def solid(r: int) -> bool:
        return rows[r][0] == rows[r][1] and bool(rows[r][0].strip())

    def step(r: int, d: int) -> int:
        """The next solid row from r in direction d, or the end of the file."""
        r += d
        while 0 <= r < len(rows) and not solid(r):
            r += d
        return min(max(r, 0), len(rows) - 1)

    def occurrences(r1: int, r2: int) -> int:
        s = edits._trim_blank_edges([old for old, _ in rows[r1:r2 + 1] if old is not None])  # as apply_one does
        return sum(a[i:i + len(s)] == s for i in range(len(a) - len(s) + 1)) if s else 0

    spans: list[list[int]] = []  # inclusive row ranges
    changed = [r for r in range(len(rows)) if rows[r][0] != rows[r][1]]
    for r in changed:
        if spans and r <= spans[-1][1] + 1:
            spans[-1][1] = r
        else:
            spans.append([r, r])
    for s in spans:
        for _ in range(up):
            s[0] = step(s[0], -1)
        for _ in range(down):
            s[1] = step(s[1], 1)
        while occurrences(*s) != 1:
            grown = [step(s[0], -1), step(s[1], 1)]
            if grown == s:
                return None
            s[:] = grown
    merged: list[list[int]] = []
    for s in sorted(spans):
        if merged and s[0] <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], s[1])
        else:
            merged.append(s)
    return [Edit(path, "\n".join(old for old, _ in rows[r1:r2 + 1] if old is not None),
                 "\n".join(new for _, new in rows[r1:r2 + 1] if new is not None)) for r1, r2 in merged]


def render(rationale: str, blocks: list[Edit]) -> str:
    """The assistant message, in the format of `edits.FORMAT_EXAMPLE`."""
    return "\n".join([f"RATIONALE: {rationale}"] + [
        f"<<<<<<< SEARCH {e.path}\n{e.search}\n=======\n{e.replace}\n>>>>>>> REPLACE" for e in blocks])


def reapplies(pre: str, post: str, path: str, target: str) -> bool:
    """The target, parsed and applied as the loop would, gives the post-fix file byte for byte."""
    proposal = edits.parse(target, {path: pre})
    if proposal.parse_error:
        return False
    try:
        return edits.apply_edits({path: pre}, proposal.edits).get(path) == post
    except edits.ApplyError:
        return False


# Unchanged lines taken above and below each changed region, tried in this order: more when an
# earlier block's new text makes a later SEARCH ambiguous, then fewer or one side only, for a
# change at the edge of what the model is shown.
CONTEXTS = ((1, 1), (3, 3), (6, 6), (0, 0), (1, 0), (0, 1), (2, 0), (0, 2))


def copyable(search: str, shown: str) -> bool:
    """True when the SEARCH lines stand together in the text the model is shown."""
    lines, text = edits._trim_blank_edges(search.split("\n")), shown.split("\n")
    return any(text[i:i + len(lines)] == lines for i in range(len(text) - len(lines) + 1))


def convert(pre: str, post: str, path: str, summary: str, shown: str | None = None) -> str | None:
    """The training target for one fix, or None when no set of blocks re-applies byte-exact.

    With `shown`, the file as the prompt shows it, every SEARCH must also be copyable from it:
    a file over 60 lines is shown as one function, and a block outside it would teach the model
    to edit code it cannot see.
    """
    rationale = " ".join(re.split(r"(?<=[.!?])\s+", " ".join(summary.split()))[:2])
    for up, down in CONTEXTS:
        blocks = to_edits(pre, post, path, up, down)
        if (blocks and (shown is None or all(copyable(e.search, shown) for e in blocks))
                and reapplies(pre, post, path, target := render(rationale, blocks))):
            return target
    return None


def finding_line(pre: str, post: str) -> int:
    """Where the finding of a mined pair points (1-based): the first changed line inside a
    function, else the first changed line. An advisory names the flawed function, not the import
    its fix adds, and the prompt shows the function around this line."""
    data = pre.encode()
    tree = context._parse(data)
    rows = [r for tag, i1, i2, _, _ in opcodes(pre, post) if tag != "equal" for r in range(min(i1, i2 - 1), i2)]
    in_function = (r for r in rows if any(n.type in context.FUNC for n in context.enclosing(tree, r)))
    return max(0, next(in_function, rows[0])) + 1


HUNK_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def split_patch(patch: str) -> dict[str, str]:
    """A git patch as {path: that file's part of it}."""
    parts = re.split(r"^diff --git a/(\S+) b/\S+$", patch, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


def apply_patch(text: str, part: str) -> str | None:
    """`text` with one file's hunks applied, or None when a hunk does not sit where it says.

    ponytail: hunks are placed by their line numbers, with no fuzz. The patches here were made
    against exactly the file they are applied to; use `git apply` if that stops being true.
    """
    if "\n\\" in part:  # "\ No newline at end of file": a change that lines cannot show
        return None
    lines, out, at = text.split("\n"), [], 0
    for hunk in re.split(r"^(?=@@ )", part, flags=re.MULTILINE)[1:]:
        head, *body = hunk.split("\n")
        start, n_old, n_new = (int(g) if g else 1 for g in HUNK_RE.match(head).groups())
        start -= bool(n_old)  # "-5,0" adds after line 5; "-5,2" starts at line 5
        if start < at:
            return None
        out += lines[at:start]
        at = start
        for row in body:
            if not n_old and not n_new:
                break
            tag, rest = row[:1] or " ", row[1:]
            if tag in " -":
                if at >= len(lines) or lines[at] != rest:
                    return None
                at, n_old = at + 1, n_old - 1
            if tag in " +":
                out.append(rest)
                n_new -= 1
        if n_old or n_new:
            return None
    return "\n".join(out + lines[at:])


# --- mining GitHub advisories ---

def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
    if not token:
        raise SystemExit("no GitHub token: set GITHUB_TOKEN or run `gh auth login`")
    return token


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _cached(name: str, fetch):
    """fetch() once; its JSON-serialisable answer is kept in CACHE/name."""
    f = CACHE / name
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    value = fetch()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(value), encoding="utf-8")
    return value


def _api(client: httpx.Client, url: str) -> httpx.Response:
    r = client.get(url)
    if r.status_code in (403, 429) and r.headers.get("x-ratelimit-remaining") == "0":
        raise SystemExit("GitHub rate limit reached; run again after the reset. The cache keeps what was fetched.")
    return r


def advisories(client: httpx.Client) -> list[dict]:
    def fetch() -> list[dict]:
        out, url = [], f"https://api.github.com/advisories?ecosystem=pip&type=reviewed&published=<{CUTOFF}&per_page=100"
        while url:
            r = _api(client, url)
            r.raise_for_status()
            out += [{"ghsa": a["ghsa_id"], "cve": a["cve_id"], "summary": a["summary"],
                     "published": a["published_at"][:10], "cwes": [c["cwe_id"] for c in a["cwes"]],
                     "packages": sorted({v["package"]["name"] for v in a["vulnerabilities"]
                                         if v["package"]["ecosystem"] == "pip"}),
                     "references": a["references"]} for a in r.json()]
            url = r.links.get("next", {}).get("url")
            print(f"\radvisories listed: {len(out)}", end="", flush=True)
        print()
        return out
    return _cached(f"advisories-before-{CUTOFF}.json", fetch)


def commit(client: httpx.Client, repo: str, sha: str) -> dict:
    def fetch() -> dict:
        r = _api(client, f"https://api.github.com/repos/{repo}/commits/{sha}")
        if r.status_code != 200:
            return {"error": r.status_code}
        c = r.json()
        return {"sha": c["sha"], "parents": [p["sha"] for p in c["parents"]],
                "files": [{k: f.get(k) for k in ("filename", "status", "additions", "deletions")} for f in c["files"]]}
    return _cached(f"commits/{repo.replace('/', '__')}@{sha}.json", fetch)


def blob(raw: httpx.Client, repo: str, sha: str, path: str) -> str | None:
    """A file at a commit with LF line ends, as the loop reads files; None if missing or not UTF-8."""
    def fetch() -> str | None:
        r = raw.get(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}")  # public: the token is not sent
        try:
            return r.content.decode("utf-8").replace("\r\n", "\n") if r.status_code == 200 else None
        except UnicodeDecodeError:
            return None
    name = hashlib.sha1(path.encode()).hexdigest()[:16]  # a deep path would pass Windows' 260-character limit
    return _cached(f"blobs/{repo.replace('/', '__')}@{sha[:12]}/{name}.json", fetch)


def mine() -> None:
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    pairs = []
    opts = {"timeout": 60, "follow_redirects": True, "transport": httpx.HTTPTransport(retries=3)}
    with httpx.Client(headers={"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"},
                      **opts) as client, httpx.Client(**opts) as raw:
        todo = advisories(client)
        for n, adv in enumerate(todo, 1):
            print(f"\r{n}/{len(todo)} advisories, {len(pairs)} pairs", end="", flush=True)
            counts[_pair(client, raw, adv, seen, pairs)] += 1
    print()
    DATA.mkdir(parents=True, exist_ok=True)
    with PAIRS.open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(p) + "\n" for p in pairs)
    print(f"{sum(counts.values())} reviewed pip advisories published before {CUTOFF}")
    for reason, k in counts.most_common():
        print(f"  {k:5d}  {reason}")
    print(f"wrote {len(pairs)} pairs to {PAIRS.relative_to(ROOT)}")


def _pair(client: httpx.Client, raw: httpx.Client, adv: dict, seen: set[str], pairs: list[dict]) -> str:
    """Append the advisory's fix pair to `pairs`. Returns 'kept' or the reason it was dropped."""
    commits = {(repo.removesuffix(".git"), sha) for ref in adv["references"] for repo, sha in COMMIT_RE.findall(ref)}
    if len(commits) != 1:
        return "dropped: not exactly one fix commit"
    repo, sha = commits.pop()
    if excluded(repo, *adv["packages"]):
        return "dropped: benchmark project (exclusion list)"
    c = commit(client, repo, sha)
    if "error" in c or len(c["parents"]) != 1:
        return "dropped: commit not found, or a merge"
    if c["sha"] in seen:
        return "dropped: same commit as an earlier advisory"
    seen.add(c["sha"])
    code = [f for f in c["files"] if not is_test(f["filename"]) and not is_doc(f["filename"])]
    if len(code) != 1 or not code[0]["filename"].endswith(".py") or code[0]["status"] != "modified":
        return "dropped: not exactly one modified non-test Python file"
    path = code[0]["filename"]
    if code[0]["additions"] + code[0]["deletions"] > MAX_CHANGED_LINES:
        return f"dropped: more than {MAX_CHANGED_LINES} changed lines"
    pre, post = blob(raw, repo, c["parents"][0], path), blob(raw, repo, c["sha"], path)
    if pre is None or post is None or pre == post:
        return "dropped: file missing, not UTF-8, or changed only in line ends"
    target = convert(pre, post, path, adv["summary"])
    if target is None:
        return "dropped: blocks do not re-apply byte-exact"
    pairs.append({"id": adv["ghsa"], "source": "ghsa", "cve": adv["cve"], "cwe": (adv["cwes"] or [""])[0],
                  "published": adv["published"], "packages": adv["packages"], "repo": repo, "commit": c["sha"],
                  "parent": c["parents"][0], "path": path, "line": finding_line(pre, post), "summary": adv["summary"],
                  "pre": pre, "post": post, "target": target})
    return "kept"


def spotcheck(n: int, seed: int) -> None:
    """doc 09 §11: of n random pairs, all n re-apply byte-exact, and none is a benchmark project."""
    pairs = _jsonl(PAIRS)
    sample = random.Random(seed).sample(pairs, min(n, len(pairs)))
    ok = [p for p in sample if reapplies(p["pre"], p["post"], p["path"], p["target"])]
    for p in sample:
        print(f"{'ok  ' if p in ok else 'FAIL'} {p['id']} {p['repo']} {p['path']} ({p['target'].count('<<<<<<< SEARCH')} blocks)")
    leaked = [p["id"] for p in pairs if excluded(p["repo"], *p["packages"]) or p["published"] >= CUTOFF]
    print(f"{len(ok)}/{len(sample)} byte-exact (seed {seed}); of all {len(pairs)} pairs, "
          f"{len(leaked)} from a benchmark project or after {CUTOFF}")
    if len(ok) != len(sample) or leaked:
        raise SystemExit(1)


# --- general bug fixes: SWE-Gym and SWE-smith (doc 09 §8) ---

# Rows on 2026-10-09. SWE-Gym is read whole. SWE-smith is sorted by repository and its rows are
# large (each lists thousands of test names), so one page of 100 in every 1,400 rows is read.
HF_ROWS = {"SWE-Gym/SWE-Gym": range(0, 2438, 100), "SWE-bench/SWE-smith": range(0, 59136, 1400)}
# Files fetched per repository. The final set keeps at most CAP per repository, after the filters.
FETCH_PER_REPO = {"SWE-Gym/SWE-Gym": 60, "SWE-bench/SWE-smith": 10}


def hf_rows(client: httpx.Client, dataset: str, offset: int) -> list[dict]:
    """100 rows of a Hugging Face dataset from its datasets-server, which needs no parquet reader."""
    def fetch() -> list[dict]:
        r = client.get("https://datasets-server.huggingface.co/rows", params={
            "dataset": dataset, "config": "default", "split": "train", "offset": offset, "length": 100})
        r.raise_for_status()
        return [{k: row["row"].get(k) for k in ("instance_id", "repo", "base_commit", "patch", "problem_statement")}
                for row in r.json()["rows"]]
    return _cached(f"hf/{dataset.replace('/', '__')}@{offset}.json", fetch)


def smith_repo(mirror: str) -> str:
    """"swesmith/owner__name.1a2b3c4d", SWE-smith's copy of a repository at a commit, as "owner/name"."""
    return mirror.split("/", 1)[1].rsplit(".", 1)[0].replace("__", "/")


def general() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    fetched: Counter[str] = Counter()
    pairs: list[dict] = []
    with httpx.Client(timeout=120, follow_redirects=True, transport=httpx.HTTPTransport(retries=3)) as raw:
        for dataset, offsets in HF_ROWS.items():
            for offset in offsets:
                for inst in hf_rows(raw, dataset, offset):
                    counts[dataset, _general(raw, dataset, inst, fetched, pairs)] += 1
                print(f"\r{dataset} rows {offset + 100}, {len(pairs)} pairs", end="", flush=True)
            print()
    with GENERAL.open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(p) + "\n" for p in pairs)
    for (dataset, reason), k in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1])):
        print(f"  {dataset:20s} {k:5d}  {reason}")
    print(f"wrote {len(pairs)} pairs to {GENERAL.relative_to(ROOT)}")


def _general(raw: httpx.Client, dataset: str, inst: dict, fetched: Counter[str], pairs: list[dict]) -> str:
    """Append the instance's fix pair to `pairs`. Returns 'kept' or the reason it was dropped."""
    smith = dataset.endswith("SWE-smith")
    repo = smith_repo(inst["repo"]) if smith else inst["repo"]
    if excluded(repo):
        return "dropped: benchmark project (exclusion list)"
    files = split_patch(inst["patch"])
    code = [f for f in files if not is_test(f) and not is_doc(f)]
    if len(code) != 1 or not code[0].endswith(".py") or "@@" not in files[code[0]]:
        return "dropped: not exactly one modified non-test Python file"
    path, title = code[0], (inst["problem_statement"] or "").strip().split("\n")[0].strip(" #")
    hunks = files[path][files[path].index("@@"):]
    if sum(line[:1] in ("+", "-") for line in hunks.split("\n")) > MAX_CHANGED_LINES:
        return f"dropped: more than {MAX_CHANGED_LINES} changed lines"
    if not title:
        return "dropped: no problem statement"
    if fetched[repo] >= FETCH_PER_REPO[dataset]:
        return "skipped: enough from this repository"
    fetched[repo] += 1
    if smith:  # the patch plants the bug in the clean file of SWE-smith's copy; the fix is its reverse
        post = blob(raw, inst["repo"], "HEAD", path)
        pre = apply_patch(post, hunks) if post is not None else None
    else:  # the patch is the fix, against base_commit
        pre = blob(raw, repo, inst["base_commit"], path)
        post = apply_patch(pre, hunks) if pre is not None else None
    if pre is None or post is None or pre == post:
        return "dropped: file missing, or the patch does not sit on it"
    target = convert(pre, post, path, title)
    if target is None:
        return "dropped: blocks do not re-apply byte-exact"
    pairs.append({"id": inst["instance_id"], "source": "swe-smith" if smith else "swe-gym", "cwe": "", "repo": repo,
                  "path": path, "line": finding_line(pre, post), "summary": title,
                  "description": inst["problem_statement"], "pre": pre, "post": post, "target": target})
    return "kept"


# --- build: every source -> examples, through the filters of doc 09 §7 ---

SOURCES = ("ghsa", "synthetic", "swe-gym", "swe-smith")
MAX_FUNCTIONS, MAX_HUNKS = 2, 6
# doc 10 §3 trains at this sequence length: a longer example would lose the end of its target.
MAX_TOKENS = 2048
# ponytail: tokens are estimated from characters. Ollama counted 4.0 characters per token over the
# student's prompts of 2026-10-09 (prompt_eval_count), and under 3.7 for 5% of them; the lower
# figure is used, so the estimate errs high. The real tokenizer is on Kaggle, with finetune.py.
CHARS_PER_TOKEN = 3.6
# Two pairs are near-duplicates when the functions their findings point at overlap this far, in
# 5-token runs with identifiers blanked (Jaccard). The first DUP_CAP stay: one function with two
# different flaws is two examples.
DUP_SIM, DUP_CAP = 0.8, 2
# Shared 13-token runs allowed between an example and one benchmark scenario, by tier. Tier C was
# written by the teacher of the synthetic examples, so one shared run drops the example. Against
# Tier A and B the limit is the generator's (about four copied lines), and no shared run may touch
# a line that the scenario's reference fix removes or adds. Every hit that is left is in
# leakage.md to be read.
LEAK_RUNS = {"A": 30, "B": 30, "C": 0}
# A pair is also dropped when its function overlaps a benchmark scenario's target function,
# vulnerable or fixed, this far by the same measure: a copy with other names.
LEAK_LIKE = 0.5
CAP = 30  # examples per CWE and repository (doc 09 §10)
GENERAL_SHARE, VAL_SHARE, SEED = 0.20, 0.05, 3407  # doc 09 §8
FORMAT_LABELS = {"FORMAT_FAIL", "SEARCH_NOT_FOUND", "SEARCH_AMBIGUOUS", "EMPTY_SEARCH", "UNKNOWN_FILE"}


def grams(code: str, n: int, blank: bool = False) -> set[tuple[str, ...]]:
    """Runs of n code tokens, split as inject_cwe.py splits them. With `blank` every identifier
    is the same token, so a copy with renamed variables still matches."""
    t = re.findall(r"\w+|[^\w\s]", code)
    if blank:
        t = [w if keyword.iskeyword(w) or not (w[0].isalpha() or w[0] == "_") else "_" for w in t]
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}


def alike(a: set, b: set) -> float:
    """Jaccard overlap of two sets of runs."""
    both = len(a & b)
    return both / ((len(a) + len(b) - both) or 1)


def function_text(src: str, name: str) -> str:
    """The lines of a function by qualified name, or all of `src` when it has no such function."""
    span = context.function_span(src, name) if name else None
    return "\n".join(src.split("\n")[span[0] - 1:span[1]]) if span else src


def n_tokens(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


def load_items() -> list[dict]:
    """Every pair of every source, with the finding its prompt will state."""
    items = [{**p, "tool": "advisory", "rule": f"advisory.{p['cwe'].lower()}", "message": p["summary"],
              "description": p["summary"]} for p in _jsonl(PAIRS)]  # worded as the Tier B findings are
    items += [{**p, "cwe": "Bug", "tool": "issue", "rule": "issue.bug", "message": p["summary"]}
              for p in _jsonl(GENERAL)]
    for it in items:  # pairs mined before finding_line existed store the first changed line
        it["line"] = finding_line(it["pre"], it["post"])
    synthetic = []
    for rec in _jsonl(SYNTHETIC / "manifest.jsonl"):
        if rec["status"] != "kept":
            continue
        d = SYNTHETIC / rec["id"]
        meta = json.loads((d / "scenario.json").read_text(encoding="utf-8"))
        path, f = meta["allowed_paths"][0], meta["finding"]
        pre = (d / "repo" / path).read_text(encoding="utf-8")
        post = apply_patch(pre, split_patch((d / "reference_fix.patch").read_text(encoding="utf-8"))[path])
        synthetic.append({"id": rec["id"], "source": "synthetic", "cwe": meta["cwe"], "repo": "synthetic",
                          "path": path, "line": f["line"], "tool": f["tool"], "rule": f["rule_id"],
                          "message": f["message"], "description": meta["description"], "pre": pre, "post": post,
                          "relaxed": "note" in rec})
    # An example that met validator check 3 only through a PoC test goes last: a cap drops it first.
    return items + sorted(synthetic, key=lambda it: it["relaxed"])


def rendered(it: dict) -> tuple[str, str, str]:
    """(the file as the prompt shows it, the first user message, the function the finding points
    at), from the functions the loop uses."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp, it["path"])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(it["pre"], encoding="utf-8", newline="\n")
        ctx = context.get_context(Path(tmp), it["path"], it["line"], [it["path"]])
    task = Task(id=it["id"], repo_path=Path(tmp), cwe=it["cwe"], description=it["description"],
                allowed_paths=[it["path"]], finding=Finding(tool=it["tool"], rule_id=it["rule"], path=it["path"],
                                                           line=it["line"], message=it["message"]))
    return ctx.files[it["path"]], prompts.first_user_message(task, ctx), function_text(it["pre"], ctx.target)


def functions_touched(pre: str, post: str) -> int:
    """How many functions or class bodies hold a changed line. A module-level line counts as none."""
    names = set()
    for src, lo, hi in ((pre, 1, 2), (post, 3, 4)):
        data = src.encode()
        tree = context._parse(data)
        for op in opcodes(pre, post):
            if op[0] != "equal":
                names |= {context.qualified_name(context.enclosing(tree, row), data) for row in range(op[lo], op[hi])}
    return len(names - {""})


def noisy(pre: str, post: str) -> bool:
    """More than MAX_HUNKS hunks, or a hunk that changes only whitespace (doc 09 §7: reformatting)."""
    a, b = pre.split("\n"), post.split("\n")
    changed = [op for op in opcodes(pre, post) if op[0] != "equal"]
    # Changed regions closer than 7 lines are one hunk, as in a unified diff with 3 lines of context.
    hunks = 1 + sum(nxt[1] - cur[2] > 6 for cur, nxt in itertools.pairwise(changed))
    return hunks > MAX_HUNKS or any("".join("".join(a[i1:i2]).split()) == "".join("".join(b[j1:j2]).split())
                                    for _, i1, i2, j1, j2 in changed)


def runs_on(text: str, rows: set[int]) -> set[tuple[str, ...]]:
    """The 13-token runs of `text` that touch one of the given lines (0-based)."""
    t = [(tok, row) for row, line in enumerate(text.split("\n")) for tok in re.findall(r"\w+|[^\w\s]", line)]
    return {tuple(tok for tok, _ in t[i:i + 13]) for i in range(len(t) - 12) if any(row in rows for _, row in t[i:i + 13])}


def benchmark() -> tuple[dict[str, set], dict[str, set], dict[str, list[set]]]:
    """Per scenario: the 13-token runs of its Python files, each patched file's fixed version
    included; those of them that touch a line its reference fix removes or adds; and the blanked
    5-token runs of its target function, vulnerable and fixed."""
    runs, answers, functions = {}, {}, {}
    for f in sorted(SCENARIOS_DIR.glob("*/scenario.json")):
        meta, repo = json.loads(f.read_text(encoding="utf-8")), f.parent / "repo"
        texts = [py.read_text(encoding="utf-8", errors="replace") for py in repo.rglob("*.py")]
        target = (repo / meta["finding"]["path"]).read_text(encoding="utf-8")
        fixed = {path: apply_patch((repo / path).read_text(encoding="utf-8"), part) for path, part in
                 split_patch((f.parent / "reference_fix.patch").read_text(encoding="utf-8")).items()}
        runs[meta["id"]] = set().union(*(grams(t, 13) for t in texts + list(fixed.values())))
        answers[meta["id"]] = set()
        for path, post in fixed.items():
            pre = (repo / path).read_text(encoding="utf-8")
            ops = [op for op in opcodes(pre, post) if op[0] != "equal"]
            answers[meta["id"]] |= (runs_on(pre, {r for _, i1, i2, _, _ in ops for r in range(i1, i2)})
                                    | runs_on(post, {r for *_, j1, j2 in ops for r in range(j1, j2)}))
        functions[meta["id"]] = [grams(function_text(text, meta["target_function"]), 5, blank=True)
                                 for text in (target, fixed[meta["finding"]["path"]])]
    return runs, answers, functions


def feedback(att: dict, cfg: dict) -> str:
    """What loop.run told the model after an attempt, rebuilt from the attempt's record in the run file."""
    if att["proposal"]["parse_error"]:
        return f"{att['proposal']['parse_error']}\nUse exactly this layout:\n{edits.FORMAT_EXAMPLE}"
    if att["sandbox"]:
        return prompts.redact(junit.summarize([Failure(**f) for f in att["sandbox"]["failures"]],
                                              cfg["feedback_token_cap"] * 4))
    if att["gate"]:
        return "Rejected by safety gates:\n" + "\n".join(att["gate"]["details"])
    return f"FORBIDDEN_PATH: {att['apply_error']}" if att["label"] == "GATE_REJECT" else att["apply_error"]


def repair_turns(run: str, items: dict[str, dict]) -> tuple[list[dict], Counter]:
    """One example per failed attempt of the student run on a kept scenario: the conversation as
    loop.run built it, up to the feedback on that attempt. The target is the scenario's fix.

    Every prompt the student was sent is on disk, and the rebuilt conversation must equal it
    (the parity check of doc 09 §5). A scenario where it does not gives no example.
    """
    header, attempts, results = bench.read_run(RUNS_DIR / f"{run}.jsonl")
    out, stats = [], Counter()
    for res in results:
        mine = [a for a in attempts if a["task_id"] == res["task_id"] and a["n"]]
        stats["scenarios"] += 1
        stats["resolved at once"] += bool(mine) and mine[0]["label"] == "RESOLVED"
        stats["resolved"] += res["resolved"]
        it = items.get(res["task_id"])
        if it is None:
            continue
        messages, older = [{"role": "user", "content": it["prompt"]}], []
        for i, att in enumerate(mine):
            adir = RUNS_DIR / run / it["id"] / f"attempt_{att['n']}"
            said = prompts.SYSTEM_PROMPT + "\n\n" + "\n\n".join(m["content"] for m in messages)
            if (adir / "prompt.txt").read_text(encoding="utf-8") != said:
                stats["parity failures"] += 1
                break
            if att["label"] == "RESOLVED":
                break
            older.append(f"attempt {att['n']}: {att['label']}")
            answer = (adir / "raw_output.txt").read_text(encoding="utf-8") or "(empty)"
            messages = [*messages, {"role": "assistant", "content": answer}, {"role": "user", "content":
                        prompts.repair_message(att["label"], feedback(att, header["config"]), older[:-1])}]
            # The next attempt's prompt is this conversation, so Ollama counted its tokens.
            sent = mine[i + 1]["proposal"]["usage"].get("input_tokens") if i + 1 < len(mine) else None
            out.append({**it, "id": f"{it['id']}#{att['n']}", "after": att["label"], "messages": messages, "sent": sent})
    return out, stats


def size(it: dict) -> int:
    """Tokens of an example, system prompt to target: Ollama's count of the prompt where the
    student was sent it, an estimate from characters for the rest."""
    said = it.get("sent") or n_tokens(prompts.SYSTEM_PROMPT + "".join(m["content"] for m in it["messages"]))
    return said + n_tokens(it["target"])


def build(student_run: str | None, max_tokens: int) -> None:
    warnings.simplefilter("ignore", SyntaxWarning)  # old code under ast.parse, in the gates
    items = load_items()
    funnel = [("Converted pairs, and synthetic examples kept by the sandbox", Counter(it["source"] for it in items))]

    def keep(step: str, ok) -> list[dict]:
        """Filter `items` in place, note what is left, and return what was dropped."""
        verdicts = [(it, ok(it)) for it in items]
        items[:] = [it for it, good in verdicts if good]
        funnel.append((step, Counter(it["source"] for it in items)))
        print(f"{len(items):5d}  {step}", flush=True)
        return [it for it, good in verdicts if not good]

    keep("Language: a Python file, and a CWE on the advisory", lambda it: it["path"].endswith(".py") and it["cwe"])
    keep(f"Size: at most {MAX_CHANGED_LINES} changed lines, in at most {MAX_FUNCTIONS} functions",
         lambda it: gates._changed_lines(it["pre"], it["post"]) <= MAX_CHANGED_LINES
         and functions_touched(it["pre"], it["post"]) <= MAX_FUNCTIONS)
    keep(f"Noise: at most {MAX_HUNKS} hunks, none of them whitespace only", lambda it: not noisy(it["pre"], it["post"]))

    def in_view(it: dict) -> bool:
        shown, it["prompt"], function = rendered(it)
        it["messages"] = [{"role": "user", "content": it["prompt"]}]
        it["grams"] = grams(function, 5, blank=True)
        it["target"] = convert(it["pre"], it["post"], it["path"], it["message"], shown)
        return it["target"] is not None

    keep("Context: every SEARCH line is in the prompt (not in doc 09)", in_view)
    keep("Gates: the fix passes the loop's safety gates (not in doc 09)",
         lambda it: gates.check({it["path"]: it["pre"]}, {it["path"]: it["post"]}, [it["path"]]).ok)

    firsts: list[dict] = []

    def fresh(it: dict) -> bool:
        twins = sum(alike(it["grams"], k["grams"]) >= DUP_SIM for k in firsts)
        if twins < DUP_CAP:
            firsts.append(it)
        return twins < DUP_CAP

    keep(f"Dedupe: at most {DUP_CAP} functions that share {DUP_SIM:.0%} of their blanked 5-token runs", fresh)
    long = keep(f"Length: prompt and target within about {max_tokens} tokens", lambda it: size(it) <= max_tokens)
    keep("Secrets: no key or token pattern",
         lambda it: not prompts._secret_reason(f"{prompts.SYSTEM_PROMPT}\n\n{it['prompt']}\n\n{it['target']}"))

    runs, answers, functions = benchmark()

    def copied(it: dict, text: str) -> bool:
        """Note the benchmark code that `text` shares. True when that is over a limit or on a fix line."""
        mine, it["text"] = grams(text, 13), text
        it["shared"] = {sid: n for sid, theirs in runs.items() if (n := len(mine & theirs))}
        it["answer"] = [sid for sid, theirs in answers.items() if mine & theirs]
        return bool(it["answer"]) or any(n > LEAK_RUNS[sid[0]] for sid, n in it["shared"].items())

    def unleaked(it: dict) -> bool:
        it["like"] = {sid: share for sid, versions in functions.items()
                      if (share := max(alike(it["grams"], v) for v in versions)) >= LEAK_LIKE}
        return not (copied(it, it["prompt"] + "\n" + it["target"]) or it["like"]
                    or excluded(it["repo"], *it.get("packages", [])) or it.get("published", "") >= CUTOFF)

    leaked = keep("Leakage: no benchmark project, no advisory after the cutoff, no copied benchmark code", unleaked)
    per: Counter[tuple[str, str]] = Counter()

    def under_cap(it: dict) -> bool:
        per[it["cwe"], it["repo"]] += 1
        return per[it["cwe"], it["repo"]] <= CAP

    keep(f"Diversity: at most {CAP} per CWE and repository", under_cap)

    repairs, student = repair_turns(student_run, {it["id"]: it for it in items}) if student_run else ([], Counter())
    long_turns = [r for r in repairs if size(r) > max_tokens]
    repairs = [r for r in repairs if size(r) <= max_tokens
               and not prompts._secret_reason("\n\n".join(m["content"] for m in r["messages"]))]
    student["failed attempts"], student["too long"] = len(repairs) + len(long_turns), len(long_turns)
    # A repair turn adds the student's edits and the sandbox's output to its scenario's prompt: the
    # same check. The format example is left out: every system prompt holds it, at inference too,
    # and it shares a line with the reference fix of A-089-01.
    leaked_turns = [r for r in repairs if copied(
        r, "\n".join(m["content"] for m in r["messages"][1:]).replace(edits.FORMAT_EXAMPLE, ""))]
    repairs = [r for r in repairs if r not in leaked_turns]
    # A turn the student was sent as its next prompt was compared with that prompt in repair_turns.
    student.update({"leaked": len(leaked_turns), "sent": sum(bool(r["sent"]) for r in repairs),
                    "after a third attempt": sum(r["id"][-1] == "3" for r in repairs)})
    lengths = (f"Over the limit of {max_tokens}: {len(long)} pairs at the length step and {len(long_turns)} repair "
               f"turns. Within {2 * max_tokens}: {sum(size(x) <= 2 * max_tokens for x in long)} and "
               f"{sum(size(x) <= 2 * max_tokens for x in long_turns)} of them.")
    # General bug fixes are GENERAL_SHARE of the set, taken one repository after another.
    seen: Counter[str] = Counter()
    turn = {}
    for it in items:
        if it["cwe"] == "Bug":
            turn[it["id"]] = (seen[it["repo"]], len(turn))
            seen[it["repo"]] += 1
    want = round(GENERAL_SHARE / (1 - GENERAL_SHARE) * (len(items) - len(turn) + len(repairs)))
    chosen = set(sorted(turn, key=turn.get)[:want])
    keep(f"Mix: general bug fixes are {GENERAL_SHARE:.0%} of the examples",
         lambda it: it["cwe"] != "Bug" or it["id"] in chosen)

    examples = [{
        "id": it["id"], "source": it["source"], "cwe": it["cwe"],
        "slice": "repair" if "after" in it else "general" if it["cwe"] == "Bug" else "first",
        "after": it.get("after", ""),
        # Format practice (doc 09 §8): a repair after a format failure, or a fix of three blocks or more.
        "format": it["after"] in FORMAT_LABELS if "after" in it else it["target"].count("<<<<<<< SEARCH") >= 3,
        # Validation holds whole repositories and whole synthetic scenarios, so no code is on both sides.
        "group": it["id"].split("#")[0] if it["source"] == "synthetic" else it["repo"],
        "relaxed": it.get("relaxed", False), "tokens": size(it),
        "messages": [{"role": "system", "content": prompts.SYSTEM_PROMPT}, *it["messages"]], "target": it["target"],
    } for it in items + repairs]
    groups = sorted({e["group"] for e in examples})
    random.Random(SEED).shuffle(groups)
    held: set[str] = set()
    for g in groups:
        if sum(e["group"] in held for e in examples) >= VAL_SHARE * len(examples):
            break
        held.add(g)
    for e in examples:
        e["split"] = "val" if e["group"] in held else "train"
    for split in ("train", "val"):
        with (DATA / f"{split}.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(e) + "\n" for e in examples if e["split"] == split)
    leaks = (items, leaked, repairs, leaked_turns)
    (DATA / "leakage.md").write_text(leakage_report(*leaks, runs), encoding="utf-8", newline="\n")
    STATS.write_text(stats_report(funnel, examples, student, student_run, leak_counts(*leaks), lengths),
                     encoding="utf-8", newline="\n")
    print(f"{len(examples)} examples, {sum(e['split'] == 'val' for e in examples)} of them in val.jsonl; "
          f"{STATS.relative_to(ROOT)} and {(DATA / 'leakage.md').relative_to(ROOT)} written")


def table(head: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head),
            *("| " + " | ".join(str(c) for c in row) + " |" for row in rows), ""]


def leak_counts(items: list[dict], leaked: list[dict], turns: list[dict], leaked_turns: list[dict]) -> str:
    """The summary lines that stats.md and leakage.md share."""
    return "\n".join([
        (f"- Pairs from a benchmark project: {sum(excluded(it['repo'], *it.get('packages', [])) for it in items)}. "
         f"Advisories published on or after {CUTOFF}: {sum(it.get('published', '') >= CUTOFF for it in items)}."),
        (f"- Dropped at the leakage step: {len(leaked)} pairs. {sum(bool(it['answer']) for it in leaked)} share a "
         "13-token run with a line that a benchmark reference fix removes or adds. The others are over the limit "
         f"of shared runs with one scenario (by tier: {', '.join(f'{t} {n}' for t, n in LEAK_RUNS.items())}), or "
         f"their function overlaps a benchmark target function by {LEAK_LIKE:.0%} or more with identifiers blanked."),
        (f"- In the set, {sum(bool(it['shared']) for it in items)} of {len(items)} pairs share at least one "
         "13-token run with a benchmark scenario, none with a fix line."),
        (f"- A repair turn adds the student's edits and the test output to its scenario's prompt. By the same "
         f"limits {len(leaked_turns)} turns were dropped, and {sum(bool(t['shared']) for t in turns)} of the "
         f"{len(turns)} in the set share a run with a benchmark scenario."),
        "- `training/data/leakage.md` lists each of them and each shared passage.", ""])


def leakage_report(items: list[dict], leaked: list[dict], turns: list[dict], leaked_turns: list[dict],
                   runs: dict[str, set]) -> str:
    """Every pair and repair turn that shares a 13-token run with benchmark code, and the shared text."""
    dropped = leaked + leaked_turns
    hit = [it for it in items + turns + dropped if it["shared"] or it["like"]]
    passages: dict[str, tuple[set, set]] = {}  # shared text -> (pairs, scenarios)
    for it in items + turns:
        t = re.findall(r"\w+|[^\w\s]", it["text"])
        for sid in it["shared"]:
            at = {i for i in range(len(t) - 12) if tuple(t[i:i + 13]) in runs[sid]}
            for start in sorted(i for i in at if i - 1 not in at):
                end = next(i for i in range(start, len(t)) if i not in at)  # the first run that is not shared
                examples, scenarios = passages.setdefault(" ".join(t[start:end + 12]), (set(), set()))
                examples.add(it["id"])
                scenarios.add(sid)
    lines = ["# Leakage report", "",
             "Written by `training/prepare_dataset.py build`. It quotes code, so it is not published.", "",
             leak_counts(items, leaked, turns, leaked_turns), "## Pairs and repair turns with a hit", "",
             "A repair turn is named `scenario#attempt`; its row counts only what the turn adds to the prompt.", ""]
    lines += table(["Pair", "Source", "Verdict", "Shared 13-token runs, by scenario", "Touches a fix line of",
                    "Function overlap"], [
        [it["id"], it["source"], "dropped" if it in dropped else "kept",
         ", ".join(f"{sid} {n}" for sid, n in sorted(it["shared"].items(), key=lambda kv: -kv[1])) or "-",
         ", ".join(it["answer"]) or "-", ", ".join(f"{sid} {share:.0%}" for sid, share in it["like"].items()) or "-"]
        for it in sorted(hit, key=lambda it: (it not in dropped, -max(it["shared"].values(), default=0)))])
    lines += ["## The shared text of what was kept", "",
              "Each passage once, longest first, with the pairs and the scenarios that hold it.", ""]
    lines += table(["Tokens", "Pairs", "Scenarios", "Text"], [
        [passage.count(" ") + 1, ", ".join(sorted(examples)), ", ".join(sorted(scenarios)),
         "`" + passage.replace("|", "\\|") + "`"]
        for passage, (examples, scenarios) in sorted(passages.items(), key=lambda kv: -kv[0].count(" "))])
    return "\n".join(lines)


def stats_report(funnel: list, examples: list[dict], student: Counter, student_run: str | None,
                 leaks: str, lengths: str) -> str:
    n = len(examples)

    def count(**want) -> int:
        return sum(all(e[k] == v for k, v in want.items()) for e in examples)

    lines = ["# Training set statistics", "",
             ("Written by `uv run python training/prepare_dataset.py build`. Counts only: the examples stay on the "
             "laptop (doc 09 §2)."), "",
             (f"**{n} examples**: {count(split='train')} in `train.jsonl` and {count(split='val')} in `val.jsonl`, "
             "which holds whole repositories and whole synthetic scenarios."), "",
             "## Filters, in the order of doc 09 §7", "",
             "Pairs left after each step. Test files and the 60-line limit were applied when the pairs were mined.", ""]
    lines += table(["Step", *SOURCES, "all"],
                   [[step, *(left[s] for s in SOURCES), sum(left.values())] for step, left in funnel])
    lines += ["## Examples by slice", ""]
    lines += table(["Slice", "Examples", "Share", "Doc 09 §8", "Sources"], [
        [name, count(slice=name), f"{count(slice=name) / n:.0%}", share,
         ", ".join(f"{s} {count(slice=name, source=s)}" for s in SOURCES if count(slice=name, source=s))]
        for name, share in (("first", "55%"), ("repair", "20%"), ("general", "20%"))]
        + [["format practice, inside the slices above", count(format=True), f"{count(format=True) / n:.0%}", "5%",
            (f"repairs after a format failure {count(format=True, slice='repair')}, fixes of 3 or more blocks "
            f"{count(format=True) - count(format=True, slice='repair')}")]])
    lines += [(f"- Checked by the sandbox (the synthetic examples, first attempts and repair turns): "
              f"{count(source='synthetic')}. The other {n - count(source='synthetic')} re-apply byte-exact and "
              "have no test."),
              (f"- Synthetic examples that met validator check 3 only through a PoC test: "
              f"{count(source='synthetic', relaxed=True)}."), ""]
    if student:
        after = Counter(e["after"] for e in examples if e["slice"] == "repair")
        lines += ["## Student pass", "",
                  f"Run `{student_run}`: the untuned student on every kept synthetic scenario, three attempts each.", "",
                  (f"- {student['scenarios']} scenarios: {student['resolved at once']} resolved at the first attempt, "
                  f"{student['resolved']} within three."),
                  f"- {student['failed attempts']} failed attempts on scenarios in the set; {student['too long']} are "
                  f"over the length limit and {student['leaked']} fail the leakage check, so {count(slice='repair')} "
                  "repair turns are in the set: "
                  + ", ".join(f"{k} after {label}" for label, k in after.most_common()) + ".",
                  (f"- Scenarios whose rebuilt conversation differs from a prompt on disk: {student['parity failures']}. "
                   f"{student['sent']} of the repair turns in the set were sent to the student as its next prompt and "
                   "were compared with it; the others end a conversation, so no prompt on disk holds them."),
                  (f"- {student['after a third attempt']} repair turns follow a third attempt, a conversation that "
                   "`repair-local` never sends."), ""]
    cwes = Counter(e["cwe"] for e in examples).most_common()
    lines += ["## By CWE", ""]
    lines += table(["CWE", "Examples", *SOURCES],
                   [[cwe, k, *(count(cwe=cwe, source=s) for s in SOURCES)] for cwe, k in cwes[:25]]
                   + [[f"{len(cwes) - 25} others", sum(k for _, k in cwes[25:]), *[""] * len(SOURCES)]])
    lines += ["## Length", "",
              (f"Tokens of prompt and target together, estimated at {CHARS_PER_TOKEN} characters per token; for a "
               "repair turn the student was sent, Ollama's own count of the prompt."), "", lengths, ""]
    bins = Counter(e["tokens"] // 256 for e in examples)
    lines += table(["Tokens", "Examples", ""], [
        [f"{b * 256}-{b * 256 + 255}", bins[b], "#" * round(40 * bins[b] / max(bins.values()))] for b in range(max(bins) + 1)])
    lines += ["## Leakage", "", leaks]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mine", help="GitHub advisories -> fix_pairs.jsonl")
    s = sub.add_parser("spotcheck", help="re-apply random pairs")
    s.add_argument("-n", type=int, default=20)
    s.add_argument("--seed", type=int, default=3407)
    sub.add_parser("general", help="SWE-Gym and SWE-smith -> general_pairs.jsonl")
    b = sub.add_parser("build", help="all sources -> train.jsonl, val.jsonl, stats.md, leakage.md")
    b.add_argument("--student-run", help="run id of `inject_cwe.py --student`; without it there are no repair turns")
    b.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="longest example kept (default: %(default)s)")
    args = p.parse_args()
    if args.cmd == "mine":
        mine()
    elif args.cmd == "general":
        general()
    elif args.cmd == "build":
        build(args.student_run, args.max_tokens)
    else:
        spotcheck(args.n, args.seed)


if __name__ == "__main__":
    main()
