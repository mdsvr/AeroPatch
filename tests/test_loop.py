"""End-to-end loop behaviour with a scripted model (needs Docker for the sandbox cases)."""

from itertools import pairwise

from conftest import needs_docker

from aeropatch import scenario
from aeropatch.agent import loop, router
from aeropatch.config import load_config
from aeropatch.models.base import Generation


def scripted(outputs):
    it = iter(outputs)

    def fake(route, messages, system, cfg, temperature, scenario_dir=None):
        item = next(it)
        return item if isinstance(item, Generation) else Generation(text=item, model="scripted")

    return fake


GOOD = """RATIONALE: bind the parameter.
<<<<<<< SEARCH app/db.py
    cur = conn.execute(f"SELECT id, name FROM users WHERE name = '{name}'")
=======
    cur = conn.execute("SELECT id, name FROM users WHERE name = ?", (name,))
>>>>>>> REPLACE"""

HALF = GOOD.replace('"SELECT id, name FROM users WHERE name = ?", (name,)',
                    '"SELECT id, name FROM users WHERE name = ?", name')


def test_format_fail_then_gate_reject_without_sandbox(monkeypatch, tmp_path):
    bad_path = GOOD.replace("SEARCH app/db.py", "SEARCH app/__init__.py")
    monkeypatch.setattr(router, "generate", scripted(["no blocks here", bad_path]))
    cfg = load_config("repair-local", attempt_plan=["local", "local"])
    res = loop.run(scenario.load("A-089-01"), cfg, tmp_path)
    labels = [a.label for a in res.attempts]
    assert labels[0] == "FORMAT_FAIL"
    assert labels[1] in ("SEARCH_NOT_FOUND", "GATE_REJECT")
    assert not res.resolved and all(a.sandbox is None for a in res.attempts)


def test_refusal_is_not_a_numbered_attempt(monkeypatch, tmp_path):
    refusal = Generation(text="", model="claude-opus-5", refusal={"provider": "anthropic", "category": "cyber"})
    monkeypatch.setattr(router, "generate", scripted([refusal, "nothing"]))
    cfg = load_config("cascade", attempt_plan=["frontier", "local"])
    res = loop.run(scenario.load("A-089-01"), cfg, tmp_path)
    assert res.attempts[0].label == "REFUSAL" and res.attempts[0].n == 0
    assert res.attempts[1].n == 1


def test_secret_prompt_is_blocked_and_recorded(monkeypatch, tmp_path):
    task = scenario.load("A-089-01")
    task.description = 'password="sensitive-placeholder-value"'

    def should_not_call_model(*args, **kwargs):
        raise AssertionError("the model must not receive a prompt containing a secret")

    monkeypatch.setattr(router, "generate", should_not_call_model)
    cfg = load_config("repair-local", attempt_plan=["local", "frontier"])
    result = loop.run(task, cfg, tmp_path)

    assert not result.resolved
    assert result.label == "SECRET_BLOCKED"
    assert [a.label for a in result.attempts] == ["SECRET_BLOCKED"]
    assert "sensitive-placeholder-value" not in (tmp_path / task.id / "report.md").read_text()


BAD = GOOD.replace("conn.execute(f", "conn.run(f")  # SEARCH never matches, so no sandbox run


def test_identical_edit_retries_hotter_then_stops_stuck(monkeypatch, tmp_path):
    temps = []

    def fake(route, messages, system, cfg, temperature, scenario_dir=None):
        temps.append(temperature)
        return Generation(text=BAD, model="scripted", cost_usd=0.01)

    monkeypatch.setattr(router, "generate", fake)
    res = loop.run(scenario.load("A-089-01"), load_config("repair-local"), tmp_path)
    assert temps == [0.2, 0.4, 0.8]
    assert [a.label for a in res.attempts] == ["SEARCH_NOT_FOUND", "STUCK"]
    assert res.label == "STUCK" and not res.resolved
    assert round(sum(a.cost_usd for a in res.attempts), 2) == 0.03  # the discarded repeat is still billed


def test_identical_edit_retry_that_differs_is_a_normal_attempt(monkeypatch, tmp_path):
    other = BAD.replace("conn.run(f", "conn.query(f")
    monkeypatch.setattr(router, "generate", scripted([BAD, BAD, other]))
    cfg = load_config("repair-local", attempt_plan=["local", "local"])
    res = loop.run(scenario.load("A-089-01"), cfg, tmp_path)
    assert [(a.n, a.label) for a in res.attempts] == [(1, "SEARCH_NOT_FOUND"), (2, "SEARCH_NOT_FOUND")]


def test_chain_of_repairs_on_top_of_each_other_still_targets_the_original(monkeypatch, tmp_path):
    original = """    cur = conn.execute(f"SELECT id, name FROM users WHERE name = '{name}'")"""
    # Each version adds a suppression marker, so every attempt stops at the gates (no Docker).
    versions = [original] + [f'    cur = conn.execute("{q}")  # nosec' for q in "abc"]
    outs = [f"<<<<<<< SEARCH app/db.py\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
            for old, new in pairwise(versions)]
    monkeypatch.setattr(router, "generate", scripted(outs))
    res = loop.run(scenario.load("A-089-01"), load_config("repair-local"), tmp_path)
    assert [a.label for a in res.attempts] == ["GATE_REJECT"] * 3  # none is SEARCH_NOT_FOUND
    assert all(a.proposal.edits[0].search == original for a in res.attempts)

    # A repair that re-states the first edit on top of itself is the same edit: STUCK.
    same = outs[0].replace(original, versions[1])
    monkeypatch.setattr(router, "generate", scripted([outs[0], same, same]))
    res = loop.run(scenario.load("A-089-01"), load_config("repair-local"), tmp_path)
    assert [a.label for a in res.attempts] == ["GATE_REJECT", "STUCK"]


@needs_docker[0]
@needs_docker[1]
def test_repair_after_failing_poc(monkeypatch, tmp_path):
    scenario.ensure_image("A-089-01")
    monkeypatch.setattr(router, "generate", scripted([HALF, GOOD]))
    cfg = load_config("repair-local", attempt_plan=["local", "local"])
    res = loop.run(scenario.load("A-089-01"), cfg, tmp_path)
    assert [a.label for a in res.attempts][-1] == "RESOLVED" and res.resolved
    assert res.attempts[0].label in ("POC_FAIL", "REGRESSION")
    assert "(name,)" in res.final_diff
    assert (tmp_path / "A-089-01" / "attempt_2" / "diff.patch").exists()
    assert (tmp_path / "A-089-01" / "report.md").read_text().count("requires human review") == 1
