"""Synthetic CWE injection (doc 09 §3): execution-verified training examples. Never eval data.

    uv run python training/inject_cwe.py --teacher <ollama tag> --count 50 --student

For each candidate a teacher model writes a small clean module, one SEARCH/REPLACE block that
plants a CWE in it, PoC tests and regression tests. A candidate is kept only when
- the block applies, changes 1-10 lines, names no flaw in a comment, and both versions parse,
- its code is not a copy of benchmark code (MAX_EVAL_OVERLAP; doc 09 §9),
- it passes validator checks 1-3 in the sandbox: the PoC fails on the injected code as a test
  failure (not an import or syntax error) and passes on the clean code, regression tests pass
  on both and catch a deleted function body. Tests that the sandbox does not bear out are
  removed first (prune_tests); at least 1 PoC test and 2 regression tests must be left.
Kept examples are scenario directories under training/synthetic/, so --student can run the
untuned SLM on them; its failed attempts and their sandbox feedback are the repair-turn material.

The teacher is any model behind an Ollama /api/chat endpoint (OLLAMA_HOST selects the server).
Use an open-weights model that is stronger than the student (doc 09 §4); the student as its own
teacher is only good for a smoke test. Whatever it writes, only sandbox-verified output is kept.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import random
import re
import shutil
import sys
import time
import tokenize
from collections import Counter
from pathlib import Path

import docker
from aeropatch import bench, scenario
from aeropatch.agent import edits, gates, prompts
from aeropatch.config import ROOT, SCENARIOS_DIR, load_config
from aeropatch.contracts import Edit
from aeropatch.models import local_client
from aeropatch.sandbox import sandbox
from aeropatch.tools import scanners
from aeropatch.tools.context import get_context
from aeropatch.tools.git_ops import Workspace

OUT = ROOT / "training" / "synthetic"  # gitignored: the script is published, the data is not (doc 09 §2)

# CWE -> (what the teacher plants, sampling weight, a PoC that separates the two versions). The
# weights oversample what the untuned SLM failed on the DEV split (NOTES.md, local-route runs of
# 2026-10-01): 3 = never or once resolved (328, 918), 2 = resolved in under half of the runs (78,
# 89, 601), 1 = the rest, including the CWEs dev has no scenario for. Test results must not shape
# the training data (doc 11 §3). The PoC ideas are there because a 9B teacher's own PoC tests
# passed on both versions (pilot of 2026-10-06); the student never sees a test.
CWES = {
    "CWE-20": ("a quantity or amount from the request is used without a range check", 1,
               "a negative and an absurdly large quantity each raise ValueError"),
    "CWE-22": ("a caller-supplied file name is joined onto a base directory and opened unchecked", 1,
               ("with tmp_path as the base directory, the name '../secret.txt' raises ValueError and the file "
               "beside the base directory is not read")),
    "CWE-78": ("a caller-supplied value is formatted into a command that runs through the shell", 2,
               ("the function takes run=subprocess.run as a parameter; a fake run records its arguments, and for the "
               "input 'x; echo pwned' the command is a list with that text as one element and shell is not True")),
    "CWE-79": ("caller-supplied text is placed into HTML without escaping", 1,
               "for the input '<script>alert(1)</script>' the returned HTML does not contain '<script>'"),
    "CWE-89": ("an sqlite3 query is built by string formatting instead of bound parameters", 2,
               "with an in-memory sqlite3 database holding two rows, the input \"x' OR '1'='1\" returns no rows"),
    "CWE-209": ("exception details or a traceback are returned to the client", 1,
                "when the operation fails, the returned message contains neither the exception's text nor 'Traceback'"),
    "CWE-327": ("MD5 or SHA-1 is used for a signature or an integrity check", 1,
                "the signature of b'data' is not the md5 or sha1 hex digest of it and is at least 64 characters long"),
    "CWE-328": ("passwords are stored as a fast unsalted digest, not a salted key-derivation function", 3,
                ("storing the same password twice gives two different stored values, and neither is the md5, sha1 or "
                "sha256 hex digest of the password")),
    "CWE-338": ("a security token is made with the random module instead of secrets", 1,
                "two tokens made after calling random.seed(1) before each are different"),
    "CWE-352": ("a state-changing POST handler skips the CSRF token check", 1,
                "a POST with a wrong CSRF token raises PermissionError and changes nothing"),
    "CWE-502": ("pickle.loads is called on bytes that come from the caller", 1,
                ("pickle.dumps of an object whose __reduce__ creates a file in tmp_path is rejected with ValueError "
                "and the file is not created")),
    "CWE-601": ("a redirect target from the request is returned without checking it is a local path", 2,
                "the targets 'https://evil.example/' and '//evil.example' give '/', and '/home' is returned unchanged"),
    "CWE-798": ('a credential is a string literal in the source (use "changeme"), not an environment variable', 1,
                "after monkeypatch.setenv sets the variable, that value is accepted and 'changeme' is refused"),
    "CWE-918": ("a caller-supplied URL goes to an injected fetch(url) callable without a host check", 3,
                ("a fake fetch records the URLs it is called with; for 'http://127.0.0.1/x', 'http://localhost/x' and "
                "'http://169.254.169.254/x' the function raises ValueError and the fake is never called")),
    "CWE-1333": ("a regular expression has a nested quantifier that backtracks exponentially", 1,
                 "the input 'a' * 26 + '!' is handled in under 2 seconds, measured with time.perf_counter"),
}
# Kept apart from the benchmark's apps (shop, invoices, logs, webhooks, profiles, queues).
THEMES = ["library loans", "gym class bookings", "a recipe box", "a bus timetable", "plant nursery stock",
          "vet clinic appointments", "conference talk submissions", "parking permits", "school grade books",
          "hotel housekeeping rosters", "bike rental", "museum ticketing", "a chess club ladder",
          "weather station readings", "a seed catalogue", "boat mooring bookings"]
SECTIONS = ("fixed", "vulnerable", "poc", "regression", "meta")
MAX_INJECTED_LINES = 10
NGRAM = 13
# Above this many shared 13-token runs (about four copied lines) a candidate is dropped as a copy
# of benchmark code. One shared idiom, such as `scheme not in ("http", "https")`, is 3 runs and
# was a false reject in the pilot of 2026-10-06. The count goes into the manifest, so the leakage
# report of prepare_dataset.py can look at every example that shares anything.
MAX_EVAL_OVERLAP = 30
# Words that tell the student where the flaw is, in the lines the teacher planted (their comments
# are cut by planted(); this is for docstrings and strings).
GIVEAWAY = re.compile(r"vulnerab|insecure|unsafe|exploit|attack|CWE-|"
                      r"\b(?:no|missing|without|skips?|removed?) (?:\w+ ){0,2}(?:check|validation|escap|saniti)", re.IGNORECASE)

SYSTEM = "You write small, realistic Python exercises for practising security fixes. Output only what is asked."
# Version 1 asked for the fixed and the vulnerable module in full: a 9B teacher rewrote docstrings
# and added helpers between the two, and 0 of 7 candidates were kept. Version 2 (the inject block)
# got the size right; its PoC tests passed on both versions. Version 3 adds a PoC idea per CWE.
# Versions 4 and 5 are the same text with changed checks: from 4 on, tests get their missing
# imports and wrong tests are pruned; from 5 on, every comment on the planted lines is cut.
PROMPT_VERSION = 5
PROMPT = """\
Write one exercise about {theme}. Vulnerability to plant: {cwe}, where {hint}.

Rules:
- Standard library only, no network access. One module, app/{module}.py, 40-80 lines, 3-6 functions with docstrings.
- fixed: the complete, secure module. Its comments and docstrings say what the code does, never that it is \
secure, fixed or vulnerable.
- inject: ONE SEARCH/REPLACE block that plants the vulnerability by changing at most {max_lines} lines inside ONE \
function. SEARCH copies lines of the fixed module exactly. REPLACE is the vulnerable version of those lines, \
with no comment about the flaw.
- poc: 1-3 pytest tests that FAIL on the vulnerable module and PASS on the fixed one. They assert behaviour, \
not how the fix is written. One that works here: {poc}.
- regression: 3-6 pytest tests of normal behaviour that PASS on both modules. At least two of them call the \
function that the block changes.
- Tests import every name they use, with `from app.{module} import ...` for the module's names.

Output exactly these five sections, with no code fences and nothing else:
=== fixed ===
=== inject ===
<<<<<<< SEARCH
<lines of the fixed module>
=======
<the vulnerable lines>
>>>>>>> REPLACE
=== poc ===
=== regression ===
=== meta ===
function: <name of the function the block changes>
description: <one sentence that states the flaw as a fact>
"""


def tokens(code: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", code)


def ngrams(code: str) -> set[tuple[str, ...]]:
    t = tokens(code)
    return {tuple(t[i:i + NGRAM]) for i in range(len(t) - NGRAM + 1)}


def parse_sections(text: str) -> dict[str, str]:
    parts = re.split(r"^=== (\w+) ===[ \t]*$", text, flags=re.MULTILINE)
    return {name: "\n".join(line for line in body.strip("\n").split("\n") if not line.startswith("```")) + "\n"
            for name, body in zip(parts[1::2], parts[2::2])}


def planted(s: dict[str, str], rel: str) -> str:
    """The vulnerable module: the fixed one with the teacher's one block applied, or '' when there
    is not exactly one block or it does not apply. Building it here is what keeps the two versions
    identical outside the planted lines."""
    fixed = s.get("fixed", "")
    blocks = [Edit(rel, e.search, e.replace) for e in edits.parse(s.get("inject", ""), {rel: fixed}).edits]
    try:
        return uncommented(edits.apply_edits({rel: fixed}, blocks)[rel], fixed) if len(blocks) == 1 else ""
    except edits.ApplyError:
        return ""


def uncommented(code: str, fixed: str) -> str:
    """`code` without the comments on its planted lines (those not in `fixed`). The teacher uses
    them to say what is missing ("# Missing upper bound check"), which hands the student the fix."""
    keep, lines = set(fixed.split("\n")), code.split("\n")
    try:
        comments = [t for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type == tokenize.COMMENT]
    except (tokenize.TokenError, SyntaxError):
        return code  # write_example rejects what does not parse
    for row, col in ((t.start[0] - 1, t.start[1]) for t in comments if lines[t.start[0] - 1] not in keep):
        lines[row] = lines[row][:col].rstrip() or None
    return "\n".join(line for line in lines if line is not None)


def add_imports(test: str, module: str, fixed: str) -> str:
    """A test file with the imports it uses but left out: the module's names, stdlib modules, pytest.

    A 9B teacher forgets one in about half of its test files (pilot of 2026-10-06), and every test
    in the file then fails with a NameError on both versions.
    """
    try:
        nodes, own = list(ast.walk(ast.parse(test))), ast.parse(fixed).body
    except SyntaxError:
        return test
    bound = ({(a.asname or a.name).split(".")[0] for n in nodes if isinstance(n, (ast.Import, ast.ImportFrom))
              for a in n.names}
             | {n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
             | {n.arg for n in nodes if isinstance(n, ast.arg)}
             | {n.id for n in nodes if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load)})
    used = {n.id for n in nodes if isinstance(n, ast.Name)} - bound
    names = used & ({n.name for n in own if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
                    | {t.id for n in own if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)})
    head = [f"from app.{module} import {', '.join(sorted(names))}"] if names else []
    head += [f"import {m}" for m in sorted(used & (sys.stdlib_module_names | {"pytest"}))]
    return "\n".join([*head, test])


def write_example(d: Path, sid: str, cwe: str, module: str, s: dict[str, str]) -> str:
    """Static checks, then the example as a scenario directory. Returns a reject reason or ''."""
    if any(not s.get(name, "").strip() for name in SECTIONS):
        return "format"
    meta = dict(line.split(":", 1) for line in s["meta"].splitlines() if ":" in line)
    target = meta.get("function", "").strip().strip("`()")
    try:
        tree = ast.parse(s["vulnerable"])
        ast.parse(s["fixed"])
    except SyntaxError:
        return "syntax"
    # A method counts, named "Class.method" as the validator and the benchmark name one. Asking
    # for top-level functions only threw away every class-based module (9 of 74 candidates).
    defs = [(n.name, n) for n in tree.body if isinstance(n, ast.FunctionDef)]
    defs += [(f"{c.name}.{n.name}", n) for c in tree.body if isinstance(c, ast.ClassDef)
             for n in c.body if isinstance(n, ast.FunctionDef)]
    target, fn = next(((name, n) for name, n in defs if target in (name, n.name)), ("", None))
    if fn is None:
        return "no_target"
    if not 0 < gates._changed_lines(s["vulnerable"], s["fixed"]) <= MAX_INJECTED_LINES:
        return "injection_size"
    rel = f"app/{module}.py"
    for sub, name, body in (("repo/app", "__init__.py", ""), ("repo/app", f"{module}.py", s["vulnerable"]),
                            ("tests_poc", "test_poc.py", add_imports(s["poc"], module, s["fixed"])),
                            ("tests_regression", "test_regression.py", add_imports(s["regression"], module, s["fixed"])),
                            ("", "requirements.lock", "# stdlib only\n")):
        (d / sub).mkdir(parents=True, exist_ok=True)
        (d / sub / name).write_text(body, encoding="utf-8", newline="\n")
    with Workspace(d / "repo") as ws:
        ws.write({rel: s["fixed"]})
        (d / "reference_fix.patch").write_text(ws.diff(), encoding="utf-8", newline="\n")
    description = meta.get("description", "").strip()
    (d / "scenario.json").write_text(json.dumps({
        "id": sid, "tier": "S", "cwe": cwe, "split": "train", "description": description,
        "finding": {"tool": "synthetic", "rule_id": f"synthetic.{cwe.lower()}", "path": rel, "line": fn.lineno,
                    "severity": "high", "message": description},
        "allowed_paths": [rel], "target_function": target, "poc_tests": ["tests_poc/test_poc.py"],
        "regression_tests": ["tests_regression/test_regression.py"], "allow_imports": [],
        "source_url": "", "license": "generated", "published_date": None}, indent=2) + "\n", encoding="utf-8")
    return ""


def drop_tests(src: str, names: set[str]) -> tuple[str, int]:
    """A test file without the named tests (top-level or in a class), and the number of tests left."""
    lines, cut, left = src.split("\n"), [], 0
    for node in ast.parse(src).body:
        group = node.body if isinstance(node, ast.ClassDef) else [node]
        tests = [n for n in group if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]
        bad = [n for n in tests if n.name in names]
        left += len(tests) - len(bad)
        cut += [node] if bad and len(bad) == len(group) else bad  # a class with nothing left goes whole
    for n in reversed(cut):
        del lines[min([n.lineno] + [dec.lineno for dec in n.decorator_list]) - 1:n.end_lineno]
    return "\n".join(lines), left


def which_test(test_id: str) -> tuple[str, str]:
    """(suite, test function) of a JUnit id such as tests_poc.test_poc.test_x[http://127.0.0.1/x]."""
    path = test_id.split("[")[0].split(".")  # a parameter can hold dots
    return ("poc" if "test_poc" in path[:-1] else "regression"), path[-1]


def prune_tests(sid: str) -> str:
    """Remove the teacher's tests that the sandbox does not bear out. Returns a reject reason or ''.

    A 9B teacher gets the module and the planted flaw right more often than every one of its
    tests: on 2026-10-06 each candidate that reached the sandbox had a wrong test. A PoC test
    stays when it fails on the vulnerable module and passes on the fixed one; a regression test
    stays when it passes on both. What is left still has to pass validator checks 1-3.
    """
    task, d = scenario.load(sid), scenario.scenario_dir(sid)
    image = scenario.ensure_image(sid)

    def failed(ws: Workspace) -> set[tuple[str, str]]:
        """(suite, test function) of every test that did not pass on the workspace."""
        return {which_test(f.test_id) for f in sandbox.run_tests(image, ws.src).failures}

    with Workspace(task.repo_path) as ws:
        on_vulnerable = failed(ws)
        ws.apply_patch((d / "reference_fix.patch").read_text(encoding="utf-8"))
        on_fixed = failed(ws)
    for suite, least, reason in (("poc", 1, "no_poc_separates"), ("regression", 2, "regression_tests_wrong")):
        f = d / f"tests_{suite}" / f"test_{suite}.py"
        src = f.read_text(encoding="utf-8")
        names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name.startswith("test")}
        if suite == "poc":
            drop = {n for n in names if (suite, n) not in on_vulnerable or (suite, n) in on_fixed}
        else:
            drop = {n for n in names if (suite, n) in on_vulnerable | on_fixed}
        text, left = drop_tests(src, drop)
        if left < least:
            return reason
        f.write_text(text, encoding="utf-8", newline="\n")
    return ""


def verify(sid: str) -> str:
    """Sandbox checks 1-3 of the scenario validator (doc 11 §6). Returns a reject reason or ''."""
    task = scenario.load(sid)
    ctx = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
    try:
        prompts.check_no_secrets(prompts.SYSTEM_PROMPT + "\n\n" + prompts.first_user_message(task, ctx))
    except prompts.SecretInPrompt:
        return "secret"
    try:
        reason = prune_tests(sid)
        if reason:
            return reason
        checks = scenario.validate(sid, rebuild=True).checks  # the image holds the tests as they were
    except Exception as e:  # noqa: BLE001 - a teacher's code can break the build or the harness
        return f"sandbox_error:{type(e).__name__}"
    note = ""
    for name in ("1_vulnerable_baseline", "2_reference_fix", "3_destructive_fix_caught"):
        if checks[name].startswith("PASS"):
            continue
        # Check 3 wants a REGRESSION test to fail once the target's body is deleted. Pruning often
        # leaves that to the PoC tests (16 of 17 check-3 rejects, 2026-10-06). For training data it
        # is enough that the deleted body is not judged RESOLVED; the manifest notes which it was.
        if name.startswith("3") and deleted_body_fails(sid):
            note = "\ncheck 3 by a PoC test"
            continue
        return f"{name}\n{checks[name]}"  # the second line goes to the rejects file, not the manifest
    # Check 1 also passes when the PoC "fails" on an import or syntax error (doc 09 §10).
    return note if "label=POC_FAIL" in checks["1_vulnerable_baseline"] else "poc_wrong_reason"


def deleted_body_fails(sid: str) -> bool:
    """True when the target function with its body replaced by `return None` fails some test."""
    task = scenario.load(sid)
    with Workspace(task.repo_path) as ws:
        scenario.destructive_patch(ws, task.finding.path, task.target_function)
        return not sandbox.run_tests(scenario.image_tag(sid), ws.src).resolved


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--teacher", required=True, help="Ollama model tag of the teacher")
    p.add_argument("--count", type=int, default=20, help="candidates to generate")
    p.add_argument("--student", action="store_true", help="then run repair-local on the kept examples")
    # A teacher larger than the VRAM needs its own split; the student's "all layers on the GPU" would not load.
    p.add_argument("--num-gpu", type=int, help="teacher layers on the GPU (default: the student's setting)")
    p.add_argument("--num-ctx", type=int, help="teacher context size (default: the student's)")
    args = p.parse_args()

    eval_ngrams = set().union(*(ngrams(f.read_text(encoding="utf-8")) for f in SCENARIOS_DIR.glob("*/repo/**/*.py")))
    OUT.mkdir(parents=True, exist_ok=True)
    # ponytail: scenario.py finds scenarios through this one module constant; pointing it at OUT
    # reuses load/validate/bench unchanged. Give them a root argument if a second caller appears.
    scenario.SCENARIOS_DIR = OUT
    manifest = OUT / "manifest.jsonl"
    done = manifest.read_text(encoding="utf-8").splitlines() if manifest.exists() else []
    seen = {json.loads(line)["sha"] for line in done}
    cfg = {**load_config("repair-local", local_model=args.teacher), "max_tokens_local": 3500}  # 4 files per answer
    cfg.update({k: v for k, v in (("local_num_gpu", args.num_gpu), ("local_num_ctx", args.num_ctx)) if v is not None})

    for seq in range(len(done) + 1, len(done) + args.count + 1):
        cwe = random.choices(list(CWES), weights=[w for _, w, _ in CWES.values()])[0]
        theme = random.choice(THEMES)
        module = re.sub(r"\W+", "_", theme.removeprefix("a ")).strip("_")
        sid = f"S-{cwe.split('-')[1]}-{seq:05d}"
        for stale in OUT.glob(f"S-*-{seq:05d}"):  # a run stopped mid-candidate left its directory, with no manifest line
            shutil.rmtree(stale)
        start = time.monotonic()
        gen = local_client.generate(
            [{"role": "user", "content": PROMPT.format(theme=theme, cwe=cwe, hint=CWES[cwe][0], poc=CWES[cwe][2],
                                                        module=module, max_lines=MAX_INJECTED_LINES)}],
            SYSTEM, cfg, 0.8)
        sections = parse_sections(gen.text)
        code = sections["vulnerable"] = planted(sections, f"app/{module}.py")
        sha = hashlib.sha256(" ".join(tokens(code)).encode()).hexdigest()[:16]
        overlap = len(ngrams(code) & eval_ngrams)
        if gen.error:
            reason = "provider_error"
        elif sections.get("inject", "").strip() and not code:
            reason = "inject_not_applied"
        elif code and sha in seen:  # an answer without the section is a format failure, not a repeat
            reason = "duplicate"
        elif overlap > MAX_EVAL_OVERLAP:
            reason = "leakage"
        elif GIVEAWAY.search("\n".join(set(code.splitlines()) - set(sections["fixed"].splitlines()))):
            reason = "gives_away"
        else:
            reason = write_example(OUT / sid, sid, cwe, module, sections) or verify(sid)
        reason, _, detail = reason.partition("\n")
        if reason:
            # The answer is kept: it is the only way to see what to change in the prompt.
            (OUT / "rejects").mkdir(exist_ok=True)
            (OUT / "rejects" / f"{sid}.txt").write_text(f"{gen.text}\n\n=== rejected: {reason} ===\n{detail or gen.error}\n",
                                                        encoding="utf-8")
            shutil.rmtree(OUT / sid, ignore_errors=True)
            try:
                docker.from_env().images.remove(scenario.image_tag(sid), force=True)
            except docker.errors.DockerException:
                pass  # no image was built
        seen.add(sha)
        rec = {"id": sid, "cwe": cwe, "theme": theme, "status": reason or "kept", "sha": sha,
               "teacher": args.teacher, "prompt": PROMPT_VERSION, "seconds": round(time.monotonic() - start, 1),
               "gen_seconds": round(gen.latency_s, 1), "out_tokens": gen.usage.get("output_tokens"),
               "eval_overlap": overlap}
        if not reason:
            if detail:
                rec["note"] = detail
            # Detectability split (doc 09 §10): flagged and unflagged examples are both kept.
            rec["scanner_flagged"] = any(f.cwe == cwe for f in scanners.scan(OUT / sid / "repo")["findings"])
        with manifest.open("a", encoding="utf-8") as out:
            out.write(json.dumps(rec) + "\n")
        print(f"{sid} {cwe} {rec['status']} ({rec['seconds']}s)", flush=True)

    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    print("all candidates so far:", dict(Counter(rec["status"] for rec in records).most_common()))
    kept = [rec["id"] for rec in records if rec["status"] == "kept"]
    if args.student and kept:
        print("student run:", bench.run_benchmark(load_config("repair-local"), "train", ids=kept))


if __name__ == "__main__":
    main()
