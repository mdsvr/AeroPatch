"""Synthetic CWE injection (doc 09 §3): execution-verified training examples. Never eval data.

    uv run python training/inject_cwe.py --teacher <ollama tag> --count 50 --student

For each candidate a teacher model writes a small clean module, the same module with one CWE
injected, PoC tests and regression tests. A candidate is kept only when
- the injection is 1-10 changed lines and both versions parse,
- its code shares no 13-token run with a benchmark scenario (leakage, doc 09 §9),
- it passes validator checks 1-3 in the sandbox: the PoC fails on the injected code as a test
  failure (not an import or syntax error) and passes on the clean code, regression tests pass
  on both and catch a deleted function body.
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
import json
import random
import re
import shutil
import time
from collections import Counter
from pathlib import Path

import docker
from aeropatch import bench, scenario
from aeropatch.agent import gates, prompts
from aeropatch.config import ROOT, SCENARIOS_DIR, load_config
from aeropatch.models import local_client
from aeropatch.tools import scanners
from aeropatch.tools.context import get_context
from aeropatch.tools.git_ops import Workspace

OUT = ROOT / "training" / "synthetic"  # gitignored: the script is published, the data is not (doc 09 §2)

# CWE -> (what the teacher plants, sampling weight). The weights oversample what the untuned SLM
# failed on the DEV split (NOTES.md, local-route runs of 2026-10-01): 3 = never or once resolved
# (328, 918), 2 = resolved in under half of the runs (78, 89, 601), 1 = the rest, including the
# CWEs dev has no scenario for. Test results must not shape the training data (doc 11 §3).
CWES = {
    "CWE-20": ("a quantity or amount from the request is used without a range check", 1),
    "CWE-22": ("a caller-supplied file name is joined onto a base directory and opened unchecked", 1),
    "CWE-78": ("a caller-supplied value is formatted into a command that runs through the shell", 2),
    "CWE-79": ("caller-supplied text is placed into HTML without escaping", 1),
    "CWE-89": ("an sqlite3 query is built by string formatting instead of bound parameters", 2),
    "CWE-209": ("exception details or a traceback are returned to the client", 1),
    "CWE-327": ("MD5 or SHA-1 is used for a signature or an integrity check", 1),
    "CWE-328": ("passwords are stored as a fast unsalted digest, not a salted key-derivation function", 3),
    "CWE-338": ("a security token is made with the random module instead of secrets", 1),
    "CWE-352": ("a state-changing POST handler skips the CSRF token check", 1),
    "CWE-502": ("pickle.loads is called on bytes that come from the caller", 1),
    "CWE-601": ("a redirect target from the request is returned without checking it is a local path", 2),
    "CWE-798": ('a credential is a string literal in the source (use "changeme"), not an environment variable', 1),
    "CWE-918": ("a caller-supplied URL goes to an injected fetch(url) callable without a host check", 3),
    "CWE-1333": ("a regular expression has a nested quantifier that backtracks exponentially", 1),
}
# Kept apart from the benchmark's apps (shop, invoices, logs, webhooks, profiles, queues).
THEMES = ["library loans", "gym class bookings", "a recipe box", "a bus timetable", "plant nursery stock",
          "vet clinic appointments", "conference talk submissions", "parking permits", "school grade books",
          "hotel housekeeping rosters", "bike rental", "museum ticketing", "a chess club ladder",
          "weather station readings", "a seed catalogue", "boat mooring bookings"]
SECTIONS = ("fixed", "vulnerable", "poc", "regression", "meta")
MAX_INJECTED_LINES = 10
NGRAM = 13

SYSTEM = "You write small, realistic Python exercises for practising security fixes. Output only what is asked."
PROMPT = """\
Write one exercise about {theme}. Vulnerability to plant: {cwe}, where {hint}.

Rules:
- Standard library only, no network access. One module, app/{module}.py, 40-80 lines, 3-6 functions with docstrings.
- The fixed module and the vulnerable module are identical except for at most {max_lines} changed lines in ONE function.
- poc: 1-3 pytest tests that FAIL on the vulnerable module and PASS on the fixed one. They assert behaviour \
(the attack input is treated as data; nothing is leaked or run), not how the fix is written.
- regression: 3-6 pytest tests of normal behaviour that PASS on both modules.
- Tests import with `from app.{module} import ...`.

Output exactly these five sections, with no code fences and nothing else:
=== fixed ===
=== vulnerable ===
=== poc ===
=== regression ===
=== meta ===
function: <name of the function that differs>
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
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == target), None)
    if fn is None:
        return "no_target"
    if not 0 < gates._changed_lines(s["vulnerable"], s["fixed"]) <= MAX_INJECTED_LINES:
        return "injection_size"
    rel = f"app/{module}.py"
    for sub, name, body in (("repo/app", "__init__.py", ""), ("repo/app", f"{module}.py", s["vulnerable"]),
                            ("tests_poc", "test_poc.py", s["poc"]),
                            ("tests_regression", "test_regression.py", s["regression"]),
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


def verify(sid: str) -> str:
    """Sandbox checks 1-3 of the scenario validator (doc 11 §6). Returns a reject reason or ''."""
    task = scenario.load(sid)
    ctx = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
    try:
        prompts.check_no_secrets(prompts.SYSTEM_PROMPT + "\n\n" + prompts.first_user_message(task, ctx))
    except prompts.SecretInPrompt:
        return "secret"
    try:
        checks = scenario.validate(sid).checks
    except Exception as e:  # noqa: BLE001 - a teacher's code can break the build or the harness
        return f"sandbox_error:{type(e).__name__}"
    for name in ("1_vulnerable_baseline", "2_reference_fix", "3_destructive_fix_caught"):
        if not checks[name].startswith("PASS"):
            return name
    # Check 1 also passes when the PoC "fails" on an import or syntax error (doc 09 §10).
    return "" if "label=POC_FAIL" in checks["1_vulnerable_baseline"] else "poc_wrong_reason"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--teacher", required=True, help="Ollama model tag of the teacher")
    p.add_argument("--count", type=int, default=20, help="candidates to generate")
    p.add_argument("--student", action="store_true", help="then run repair-local on the kept examples")
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

    for seq in range(len(done) + 1, len(done) + args.count + 1):
        cwe = random.choices(list(CWES), weights=[w for _, w in CWES.values()])[0]
        theme = random.choice(THEMES)
        module = re.sub(r"\W+", "_", theme.removeprefix("a ")).strip("_")
        sid = f"S-{cwe.split('-')[1]}-{seq:05d}"
        start = time.monotonic()
        gen = local_client.generate(
            [{"role": "user", "content": PROMPT.format(theme=theme, cwe=cwe, hint=CWES[cwe][0], module=module,
                                                        max_lines=MAX_INJECTED_LINES)}], SYSTEM, cfg, 0.8)
        sections = parse_sections(gen.text)
        code = sections.get("vulnerable", "")
        sha = hashlib.sha256(" ".join(tokens(code)).encode()).hexdigest()[:16]
        if gen.error:
            reason = "provider_error"
        elif code.strip() and sha in seen:  # an answer without the section is a format failure, not a repeat
            reason = "duplicate"
        elif ngrams(code) & eval_ngrams:
            reason = "leakage"
        else:
            reason = write_example(OUT / sid, sid, cwe, module, sections) or verify(sid)
        if reason:
            shutil.rmtree(OUT / sid, ignore_errors=True)
            try:
                docker.from_env().images.remove(scenario.image_tag(sid), force=True)
            except docker.errors.DockerException:
                pass  # no image was built
        seen.add(sha)
        rec = {"id": sid, "cwe": cwe, "theme": theme, "status": reason or "kept", "sha": sha,
               "teacher": args.teacher, "seconds": round(time.monotonic() - start, 1)}
        if not reason:
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
