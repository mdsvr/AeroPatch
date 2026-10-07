"""Training data preparation (doc 09). So far: real security fix pairs from GitHub advisories.

    uv run python training/prepare_dataset.py mine        # advisories -> training/data/fix_pairs.jsonl
    uv run python training/prepare_dataset.py spotcheck   # 20 random pairs re-applied, byte-exact

`mine` lists the reviewed pip advisories published before CUTOFF, keeps those whose one fix commit
changes exactly one non-test Python file by at most 60 lines, and turns each fix into the
assistant message the model is trained to write: RATIONALE plus SEARCH/REPLACE blocks (doc 09 §6).
A pair is kept only if that message, parsed and applied by the real `aeropatch.agent.edits`,
turns the pre-fix file into the post-fix file byte for byte.

Needs a GitHub token (GITHUB_TOKEN, or a logged-in `gh`). API answers are cached under
training/data/cache/, so a second run costs nothing and a stopped run resumes.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import random
import re
import subprocess
from collections import Counter

import httpx

from aeropatch.agent import edits
from aeropatch.config import ROOT
from aeropatch.contracts import Edit

DATA = ROOT / "training" / "data"  # gitignored: the script is published, the data is not (doc 09 §2)
CACHE = DATA / "cache"
PAIRS = DATA / "fix_pairs.jsonl"

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

def to_edits(pre: str, post: str, path: str, ctx: int = 1) -> list[Edit] | None:
    """One block per changed region, with `ctx` or more unchanged lines on each side.

    A block starts and ends on an unchanged, non-blank line, because `edits.apply_one` trims
    blank lines off both ends of SEARCH and REPLACE, and grows until its SEARCH text occurs once
    in the file. Returns None when a block cannot be made unique.
    """
    a, b = pre.split("\n"), post.split("\n")
    rows: list[tuple[str | None, str | None]] = []  # the two files side by side: (old line, new line)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
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
        for _ in range(ctx):
            s[0], s[1] = step(s[0], -1), step(s[1], 1)
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


def convert(pre: str, post: str, path: str, summary: str) -> str | None:
    """The training target for one fix, or None when no set of blocks re-applies byte-exact."""
    rationale = " ".join(re.split(r"(?<=[.!?])\s+", " ".join(summary.split()))[:2])
    for ctx in (1, 3, 6):  # more context when an earlier block's new text makes a later SEARCH ambiguous
        blocks = to_edits(pre, post, path, ctx)
        if blocks and reapplies(pre, post, path, target := render(rationale, blocks)):
            return target
    return None


# --- mining GitHub advisories ---

def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
    if not token:
        raise SystemExit("no GitHub token: set GITHUB_TOKEN or run `gh auth login`")
    return token


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
    line = next(i for i, (x, y) in enumerate(zip(pre.split("\n") + [None], post.split("\n") + [None]), 1) if x != y)
    pairs.append({"id": adv["ghsa"], "source": "ghsa", "cve": adv["cve"], "cwe": (adv["cwes"] or [""])[0],
                  "published": adv["published"], "packages": adv["packages"], "repo": repo, "commit": c["sha"],
                  "parent": c["parents"][0], "path": path, "line": line, "summary": adv["summary"],
                  "pre": pre, "post": post, "target": target})
    return "kept"


def spotcheck(n: int, seed: int) -> None:
    """doc 09 §11: of n random pairs, all n re-apply byte-exact, and none is a benchmark project."""
    pairs = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    sample = random.Random(seed).sample(pairs, min(n, len(pairs)))
    ok = [p for p in sample if reapplies(p["pre"], p["post"], p["path"], p["target"])]
    for p in sample:
        print(f"{'ok  ' if p in ok else 'FAIL'} {p['id']} {p['repo']} {p['path']} ({p['target'].count('<<<<<<< SEARCH')} blocks)")
    leaked = [p["id"] for p in pairs if excluded(p["repo"], *p["packages"]) or p["published"] >= CUTOFF]
    print(f"{len(ok)}/{len(sample)} byte-exact (seed {seed}); of all {len(pairs)} pairs, "
          f"{len(leaked)} from a benchmark project or after {CUTOFF}")
    if len(ok) != len(sample) or leaked:
        raise SystemExit(1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mine", help="GitHub advisories -> fix_pairs.jsonl")
    s = sub.add_parser("spotcheck", help="re-apply random pairs")
    s.add_argument("-n", type=int, default=20)
    s.add_argument("--seed", type=int, default=3407)
    args = p.parse_args()
    if args.cmd == "mine":
        mine()
    else:
        spotcheck(args.n, args.seed)


if __name__ == "__main__":
    main()
