"""Labels a user sees, and the label the repair prompt shows the model (doc 17 part 1 §4, part 2 §2).

Both are pure functions of one attempt's recorded checks. A suite in `hidden` still ran, and its
result stays in the record as the truth, but neither label may depend on it: that is what lets the
benchmark measure how often each user label is right.
"""

from __future__ import annotations

from aeropatch.contracts import SandboxResult
from aeropatch.sandbox import junit

ATTACK_BLOCKED = "Attack test now blocked"
QUIET_TESTS_PASS = "Scanner quiet, your tests still pass"
TESTS_PASS_NO_RESCAN = "Your tests still pass; the scanner could not re-check this"
QUIET_NOT_TESTED = "Scanner quiet, not tested"
NOT_FIXED = "Not fixed, warning kept"

# A run without its PoC in view stops on one of these instead of on RESOLVED.
OFFERED = (ATTACK_BLOCKED, QUIET_TESTS_PASS, TESTS_PASS_NO_RESCAN, QUIET_NOT_TESTED)

# The model-facing label when every visible check passed but the finding's rule still fires.
SCANNER_STILL_FLAGS = "SCANNER_STILL_FLAGS"

def _whole_run_failed(sb: SandboxResult) -> bool:
    """The container timed out or never finished: no suite's result can be read. A single test's
    timeout is not this: its failures carry their suite, and a hidden suite's stays hidden."""
    return sb.timed_out or sb.label == "SANDBOX_ERROR"


def visible_suites(sb: SandboxResult, hidden: list[str]) -> list[str]:
    if sb.label == "NOT_RUN":  # the Suggest level: nothing ran
        return []
    return [s for s in ("poc", "regression") if s not in hidden]


def _passed(sb: SandboxResult, suite: str) -> bool:
    return sb.poc_passed if suite == "poc" else sb.regressions_passed


def user_label(sb: SandboxResult | None, hidden: list[str]) -> str:
    """The label a user would be shown. `sb` is None when the edit never reached the sandbox
    (a format error, a gate rejection, a refusal)."""
    if sb is None or _whole_run_failed(sb):
        return NOT_FIXED
    suites = visible_suites(sb, hidden)
    if any(not _passed(sb, s) for s in suites):
        return NOT_FIXED
    rule = sb.original_rule_present
    if rule:
        return NOT_FIXED
    if "poc" in suites and rule is False:  # part 1 §4: the attack test passes and the rule is gone
        return ATTACK_BLOCKED
    if "regression" in suites:
        return QUIET_TESTS_PASS if rule is False else TESTS_PASS_NO_RESCAN
    # ponytail: pytest exit 5 (a folder with no tests) is treated as "not tested" by the folder
    # runner in doc 17 part 4; the benchmark always has a regression suite.
    return QUIET_NOT_TESTED if rule is False else NOT_FIXED


def model_label(sb: SandboxResult, hidden: list[str], rescan_feedback: bool) -> str:
    """The result word in the repair prompt. With nothing hidden and no re-scan feedback it is the
    sandbox's own label, so every earlier config's prompts are unchanged."""
    if not hidden and not rescan_feedback and sb.label != "NOT_RUN":
        return sb.label
    # ponytail: a whole-container timeout cannot be pinned on one suite, so it is shown even when
    # a hidden suite caused it (rare: a PoC that hangs past the 300 s container limit). A per-test
    # timeout (30 s) is a suite failure and goes through the visible-suite rule below.
    if _whole_run_failed(sb):
        return sb.label
    labels = []
    for s in visible_suites(sb, hidden):
        if not _passed(sb, s):
            fails = [f for f in sb.failures if f.suite == s]
            labels.append(junit.classify(fails) or ("POC_FAIL" if s == "poc" else "REGRESSION"))
    if labels:
        specific = [lab for lab in labels if lab not in ("POC_FAIL", "REGRESSION")]
        return specific[0] if specific else ("REGRESSION" if "REGRESSION" in labels else "POC_FAIL")
    if rescan_feedback and sb.original_rule_present:
        return SCANNER_STILL_FLAGS
    return "RESOLVED" if not hidden and sb.label != "NOT_RUN" else "CHECKS_PASSED"


def visible_failures(sb: SandboxResult, hidden: list[str]) -> list:
    shown = visible_suites(sb, hidden)
    return [f for f in sb.failures if f.suite in shown or (not f.suite and not hidden)]
