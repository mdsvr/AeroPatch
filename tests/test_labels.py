"""User labels and the model-facing label over recorded sandbox results (doc 17 part 2 §2)."""

import pytest

from aeropatch import labels as L
from aeropatch.contracts import Failure, SandboxResult

POC = Failure(test_id="tests_poc/test_poc.py::test_x", kind="failure", message="exploit worked", suite="poc")
POC_IMPORT = Failure(test_id="tests_poc/test_poc.py", kind="error", message="collection failure",
                     trace="ModuleNotFoundError: No module named 'x'", suite="poc")
REG = Failure(test_id="tests_regression/test_r.py::test_y", kind="failure", message="assert 1 == 2",
              suite="regression")


def sb(label, poc=False, reg=False, rule=None, failures=(), timed_out=False):
    return SandboxResult(applied=True, poc_passed=poc, regressions_passed=reg, original_rule_present=rule,
                         failures=list(failures), label=label, timed_out=timed_out)


V1, V2 = ["poc"], ["poc", "regression"]
RESOLVED_QUIET = sb("RESOLVED", True, True, rule=False)
POC_FAILS_QUIET = sb("POC_FAIL", False, True, rule=False, failures=[POC])

USER = [
    (None, [], L.NOT_FIXED),  # the edit never reached the sandbox
    (RESOLVED_QUIET, [], L.ATTACK_BLOCKED),
    # Nothing hidden, no re-scan answer: the tests passed, but "attack blocked" needs the rule gone too.
    (sb("RESOLVED", True, True, rule=None), [], L.TESTS_PASS_NO_RESCAN),
    (sb("RESOLVED", True, True, rule=True), [], L.NOT_FIXED),
    (sb("REGRESSION", True, False, rule=False, failures=[REG]), [], L.NOT_FIXED),
    (POC_FAILS_QUIET, V1, L.QUIET_TESTS_PASS),
    (sb("POC_FAIL", False, True, rule=None, failures=[POC]), V1, L.TESTS_PASS_NO_RESCAN),
    (sb("RESOLVED", True, True, rule=True), V1, L.NOT_FIXED),
    (sb("REGRESSION", True, False, rule=False, failures=[REG]), V1, L.NOT_FIXED),
    (sb("POC_FAIL", False, False, rule=False, failures=[POC, REG]), V2, L.QUIET_NOT_TESTED),
    (sb("RESOLVED", True, True, rule=None), V2, L.NOT_FIXED),  # no re-scan is never quiet
    (sb("NOT_RUN", rule=False), V2, L.QUIET_NOT_TESTED),
    (sb("NOT_RUN", rule=None), V2, L.NOT_FIXED),
    (sb("NOT_RUN", rule=True), V2, L.NOT_FIXED),
    (sb("TIMEOUT", True, True, rule=False, timed_out=True), V2, L.NOT_FIXED),
    (sb("SANDBOX_ERROR", rule=False), V2, L.NOT_FIXED),
    (sb("TIMEOUT", True, True, rule=False, timed_out=True), [], L.NOT_FIXED),
]


@pytest.mark.parametrize(("result", "hidden", "want"), USER)
def test_user_label(result, hidden, want):
    assert L.user_label(result, hidden) == want


MODEL = [
    # Nothing hidden, no re-scan feedback: the sandbox's own label, whatever the re-scan says.
    (sb("RESOLVED", True, True, rule=True), [], False, "RESOLVED"),
    (sb("POC_FAIL", False, True, rule=True, failures=[POC]), [], False, "POC_FAIL"),
    (sb("IMPORT_ERROR", False, False, failures=[POC_IMPORT, REG]), [], False, "IMPORT_ERROR"),
    (sb("TIMEOUT"), [], False, "TIMEOUT"),
    # V1: the PoC's verdict never shows.
    (sb("IMPORT_ERROR", False, False, rule=True, failures=[POC_IMPORT, REG]), V1, True, "REGRESSION"),
    (sb("POC_FAIL", False, True, rule=True, failures=[POC]), V1, True, L.SCANNER_STILL_FLAGS),
    (sb("RESOLVED", True, True, rule=True), V1, True, L.SCANNER_STILL_FLAGS),
    (POC_FAILS_QUIET, V1, True, "CHECKS_PASSED"),
    # V2 and the Suggest level read the same.
    (sb("REGRESSION", True, False, rule=True, failures=[REG]), V2, True, L.SCANNER_STILL_FLAGS),
    (sb("NOT_RUN", rule=True), V2, True, L.SCANNER_STILL_FLAGS),
    (sb("NOT_RUN", rule=None), V2, True, "CHECKS_PASSED"),
    (sb("SANDBOX_ERROR"), V2, True, "SANDBOX_ERROR"),
]


@pytest.mark.parametrize(("result", "hidden", "rescan", "want"), MODEL)
def test_model_label(result, hidden, rescan, want):
    assert L.model_label(result, hidden, rescan) == want


def test_visible_failures_drop_the_hidden_suites():
    both = sb("POC_FAIL", False, False, failures=[POC, POC_IMPORT, REG])
    assert L.visible_failures(both, []) == [POC, POC_IMPORT, REG]
    assert L.visible_failures(both, V1) == [REG]
    assert L.visible_failures(both, V2) == []
    untagged = Failure(test_id="t", kind="error", message="m")
    assert L.visible_failures(sb("REGRESSION", failures=[untagged]), []) == [untagged]
    assert L.visible_failures(sb("REGRESSION", failures=[untagged]), V1) == []  # unknown suite: hide it


POC_HANG = Failure(test_id="tests_poc/test_poc.py::test_redos", kind="failure",
                   message="Failed: Timeout (>30.0s) from pytest-timeout", suite="poc")


def test_a_hidden_per_test_timeout_stays_hidden():
    """A PoC test that hits pytest-timeout gives the sandbox label TIMEOUT, but the container
    finished: the timeout belongs to the hidden suite and must not reach the label or the prompt."""
    hung = sb("TIMEOUT", False, True, rule=False, failures=[POC_HANG])
    assert L.user_label(hung, ["poc"]) == L.QUIET_TESTS_PASS
    assert L.model_label(hung, ["poc"], True) != "TIMEOUT"
    assert L.visible_failures(hung, ["poc"]) == []
    # V2 must match the Suggest level, which never runs the suite at all.
    assert L.user_label(hung, ["poc", "regression"]) == L.user_label(sb("NOT_RUN", rule=False), []) \
        == L.QUIET_NOT_TESTED
    # A visible suite's timeout is a plain failure of that suite.
    assert L.user_label(hung, []) == L.NOT_FIXED
    assert L.model_label(hung, [], True) == "TIMEOUT"


def test_a_whole_container_timeout_is_never_offered():
    whole = SandboxResult(applied=True, poc_passed=False, regressions_passed=False, original_rule_present=False,
                          label="TIMEOUT", timed_out=True)
    assert L.user_label(whole, ["poc"]) == L.NOT_FIXED
    assert L.model_label(whole, ["poc"], True) == "TIMEOUT"
