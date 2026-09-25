"""End-to-end loop behaviour with a scripted model (needs Docker for the sandbox cases)."""

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
