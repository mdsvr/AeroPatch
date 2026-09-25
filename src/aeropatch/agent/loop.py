"""The remediation loop: a plain state machine (doc 08 part 1, §2).

Week 1 runs it single-shot (attempt_plan of length 1). The same code walks longer plans with
repair feedback; Week 2 adds identical-edit detection and the cascade escalation triggers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from aeropatch.agent import edits, gates, prompts, router
from aeropatch.contracts import Attempt, RunResult, Task
from aeropatch.sandbox import junit, sandbox
from aeropatch.scenario import scenario_dir
from aeropatch.tools.context import get_context
from aeropatch.tools.git_ops import Workspace
from aeropatch.tools.paths import PathError

# Primary failure causes for attribution (doc 05 §9).
ATTRIBUTION = {
    "FORMAT_FAIL": "FORMAT_FAIL", "SEARCH_NOT_FOUND": "FORMAT_FAIL", "SEARCH_AMBIGUOUS": "FORMAT_FAIL",
    "UNKNOWN_FILE": "FORMAT_FAIL", "EMPTY_SEARCH": "FORMAT_FAIL", "GATE_REJECT": "GATE_REJECT",
    "POC_FAIL": "POC_STILL_FAILS", "REGRESSION": "REGRESSION", "TIMEOUT": "TIMEOUT",
    "REFUSAL": "REFUSAL", "PROVIDER_ERROR": "PROVIDER_ERROR", "BUDGET_EXHAUSTED": "BUDGET_EXHAUSTED",
    "SYNTAX_ERROR": "REGRESSION", "IMPORT_ERROR": "REGRESSION", "COLLECTION_ERROR": "REGRESSION",
    "SANDBOX_ERROR": "SANDBOX_ERROR",
}


def _save(dirpath: Path | None, name: str, text: str) -> None:
    if dirpath is None:
        return
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(text, encoding="utf-8")


def run(task: Task, cfg: dict, run_dir: Path | None = None) -> RunResult:
    start = time.monotonic()
    sdir = scenario_dir(task.id)
    task_dir = run_dir / task.id if run_dir else None
    # Week 1 uses oracle localization: the finding location is given (doc 11 §7).
    context = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
    messages = [{"role": "user", "content": prompts.first_user_message(task, context)}]
    attempts: list[Attempt] = []
    older: list[str] = []
    n = 0
    spent = 0.0
    final_diff = ""

    with Workspace(task.repo_path) as ws:
        originals = ws.read_many(task.allowed_paths)
        for i, route in enumerate(cfg["attempt_plan"]):
            temperature = cfg["temperature_first"] if n == 0 else cfg["temperature_repair"]
            prompt_text = prompts.SYSTEM_PROMPT + "\n\n" + "\n\n".join(m["content"] for m in messages)
            if route != "oracle":
                prompts.check_no_secrets(prompt_text)
            gen = router.generate(route, messages, prompts.SYSTEM_PROMPT, cfg, temperature, sdir)
            spent += gen.cost_usd
            if gen.refusal or gen.error:
                # Refusals and provider errors use up the plan entry but are not numbered attempts.
                label = "REFUSAL" if gen.refusal else "PROVIDER_ERROR"
                attempts.append(Attempt(n=0, route=route, model=gen.model, label=label,
                                        latency_s=round(gen.latency_s, 2), cost_usd=gen.cost_usd,
                                        refusal=gen.refusal, apply_error=gen.error))
                continue
            n += 1
            adir = task_dir / f"attempt_{n}" if task_dir else None
            _save(adir, "prompt.txt", prompt_text)
            _save(adir, "raw_output.txt", gen.text)
            att = Attempt(n=n, route=route, model=gen.model, latency_s=round(gen.latency_s, 2),
                          cost_usd=gen.cost_usd)
            proposal = edits.parse(gen.text)
            proposal.model, proposal.usage = gen.model, gen.usage
            att.proposal = proposal
            feedback = ""
            ws.reset()
            if proposal.parse_error:
                att.label, feedback = "FORMAT_FAIL", proposal.parse_error
            else:
                try:
                    paths = sorted({e.path for e in proposal.edits})
                    current = {**originals, **ws.read_many([p for p in paths if p not in originals])}
                    changed = edits.apply_edits(current, proposal.edits)
                except edits.ApplyError as e:
                    att.label, att.apply_error, feedback = e.code, e.message, e.message
                except PathError as e:
                    att.label, att.apply_error = "GATE_REJECT", str(e)
                    feedback = f"FORBIDDEN_PATH: {e}"
                else:
                    before = {**current}
                    att.gate = gates.check(before, changed, task.allowed_paths, cfg, task.allow_imports)
                    if not att.gate.ok:
                        att.label = "GATE_REJECT"
                        feedback = "Rejected by safety gates:\n" + "\n".join(att.gate.details)
                    else:
                        ws.write(changed)
                        att.diff = ws.diff()
                        _save(adir, "diff.patch", att.diff)
                        att.sandbox = sandbox.run_tests(
                            task.image, ws.src, cfg, adir / "sandbox_raw.log" if adir else None)
                        _save(adir, "sandbox.json", att.sandbox.to_json())
                        att.label = att.sandbox.label
                        feedback = junit.summarize(att.sandbox.failures, cfg["feedback_token_cap"] * 4)
            attempts.append(att)
            if att.label == "RESOLVED":
                final_diff = att.diff
                break
            older.append(f"attempt {n}: {att.label}")
            messages.append({"role": "assistant", "content": gen.text or "(empty)"})
            messages.append({"role": "user", "content": prompts.repair_message(att.label, feedback, older[:-1])})
            if spent >= cfg["max_usd_per_scenario"] and i < len(cfg["attempt_plan"]) - 1:
                attempts.append(Attempt(n=0, route="-", label="BUDGET_EXHAUSTED"))
                break
            if time.monotonic() - start > cfg["scenario_wallclock_s"]:
                attempts.append(Attempt(n=0, route="-", label="BUDGET_EXHAUSTED"))
                break

    resolved = bool(attempts) and attempts[-1].label == "RESOLVED"
    last = attempts[-1].label if attempts else "NO_ATTEMPT"
    result = RunResult(task_id=task.id, config=cfg["name"], attempts=attempts, resolved=resolved,
                       label="RESOLVED" if resolved else ATTRIBUTION.get(last, last),
                       final_diff=final_diff, duration_s=round(time.monotonic() - start, 2))
    if task_dir:
        _save(task_dir, "result.json", json.dumps(result.to_dict(), default=str, indent=2))
        _save(task_dir, "report.md", report_md(task, result))
    return result


def report_md(task: Task, result: RunResult) -> str:
    lines = [f"# AeroPatch report: {task.id}", "",
             "**Candidate fix, requires human review.** A passing PoC test is evidence, not proof.", "",
             f"- Finding: {task.cwe} `{task.finding.rule_id}` at `{task.finding.path}:{task.finding.line}`",
             f"- Config: `{result.config}`", f"- Outcome: **{result.label}** after {len(result.attempts)} plan entries",
             f"- Cost: ${sum(a.cost_usd for a in result.attempts):.4f}", "", "## Attempts", ""]
    for a in result.attempts:
        sb = a.sandbox
        tests = f" poc={sb.poc_passed} regressions={sb.regressions_passed}" if sb else ""
        lines.append(f"- #{a.n} {a.route} ({a.model}): {a.label}{tests}, {a.latency_s}s")
    if result.final_diff:
        lines += ["", "## Diff", "", "```diff", result.final_diff.rstrip(), "```"]
    return "\n".join(lines) + "\n"
