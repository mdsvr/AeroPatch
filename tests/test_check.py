"""Phase 1a, `aeropatch check` (doc 17 part 3): triage, cards, secrets, the page, dismissals."""

import hashlib
import html
import json
import shutil

import pytest

from aeropatch import check, config, scenario
from aeropatch.contracts import Finding
from aeropatch.tools import scanners

needs_opengrep = pytest.mark.skipif(scanners.opengrep_binary() is None, reason="opengrep/semgrep not installed")
SECRET = "Zq8vR2xpL9wTk4"  # not a placeholder, long enough for prompts.redact and _secret_reason


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Results go to a temporary runs folder, and the built-in cards are used unless a test says
    otherwise, so no test depends on the texts in rules/cards.json."""
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(check, "CARDS_PATH", tmp_path / "no-cards.json")


@pytest.fixture
def proj(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    return d


def fnd(path="app/main.py", line=1, tool="opengrep", rule_id="aeropatch.python.sqli-string-query", severity="high",
        confidence="", cwe="CWE-89", message="m") -> Finding:
    return Finding(tool=tool, rule_id=rule_id, path=path, line=line, cwe=cwe, severity=severity, message=message,
                   confidence=confidence, fingerprint=f"{rule_id}|{path}|{line}")


def snapshot(root) -> dict:
    """Every path under root, directories included, with a hash for each file."""
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir"
            for p in root.rglob("*")}


def test_check_leaves_the_folder_byte_identical(proj):
    shutil.copytree(scenario.load("A-078-04").repo_path, proj, dirs_exist_ok=True)
    (proj / "tests").mkdir(exist_ok=True)
    (proj / "tests" / "test_run.py").write_text("import subprocess\nsubprocess.call('ls', shell=True)\n")
    (proj / ".aeropatch").mkdir()
    (proj / ".aeropatch" / "dismissed.json").write_text('{"0123456789abcdef": {"reason": "r", "date": "2026-10-01"}}\n')
    before = snapshot(proj)
    res = check.check_folder(proj)
    check.format_text(res, show_all=True)
    check.write_html(res)
    assert snapshot(proj) == before
    assert res.shown and (res.run_dir / "check.json").is_file() and (res.run_dir / "report.html").is_file()
    assert res.run_dir.parent == config.RUNS_DIR / "folders" and res.run_dir.name.startswith("proj-")


def test_test_code_and_tool_folders_are_set_aside(proj):
    aside = {"tests/test_a.py": check.IN_TESTS, "pkg/tests/helpers.py": check.IN_TESTS, "test_b.py": check.IN_TESTS,
             "src/c_test.py": check.IN_TESTS, "conftest.py": check.IN_TESTS, ".venv/lib/site.py": check.IN_TOOLS,
             "node_modules/x/y.py": check.IN_TOOLS, "build/lib/z.py": check.IN_TOOLS,
             "foo.egg-info/w.py": check.IN_TOOLS}
    res = check.triage(proj, [fnd(p) for p in aside] + [fnd("app/main.py")])
    assert [c.finding.path for c in res.shown] == ["app/main.py"]
    assert {f.path: r for f, r in res.parked} == aside


def test_the_same_rule_twice_on_one_line_is_one_card(proj):
    """Opengrep reported url-prefix-allowlist twice on Quintyx demo.py:74 (2026-10-24)."""
    res = check.triage(proj, [fnd("app.py", 10), fnd("app.py", 10)])
    assert len(res.shown) == 1


def test_merge_across_tools_keeps_opengrep_before_the_unsure_step(proj):
    og, og2 = fnd("app.py", 10), fnd("app.py", 11, rule_id="aeropatch.python.subprocess-shell", cwe="CWE-78")
    # Bandit's B608 comes out at LOW confidence: merged first, so the Opengrep finding survives.
    b608 = fnd("app.py", 9, tool="bandit", rule_id="B608", severity="medium", confidence="low")
    b602 = fnd("app.py", 13, tool="bandit", rule_id="B602", confidence="high")  # nearer og2
    far = fnd("app.py", 15, tool="bandit", rule_id="B201", confidence="high")  # 4 lines from og2
    other = fnd("other.py", 10, tool="bandit", rule_id="B602", confidence="high")
    res = check.triage(proj, [og, og2, b608, b602, far, other])
    merged = {(c.finding.path, c.finding.line): [a.rule_id for a in c.also] for c in res.shown}
    assert merged == {("app.py", 10): ["B608"], ("app.py", 11): ["B602"], ("app.py", 15): [], ("other.py", 10): []}
    assert res.parked == []
    alone = check.triage(proj, [b608])  # with no Opengrep finding near it, the plan's rule sets it aside
    assert alone.shown == [] and alone.parked == [(b608, check.UNSURE)]


def test_bandit_low_confidence_or_severity_is_set_aside(proj):
    unsure = [fnd("a.py", tool="bandit", rule_id="B101", confidence="low"),
              fnd("b.py", tool="bandit", rule_id="B404", severity="low", confidence="high")]
    sure = fnd("c.py", tool="bandit", rule_id="B602", severity="medium", confidence="medium")
    res = check.triage(proj, [*unsure, sure])
    assert [c.finding.path for c in res.shown] == ["c.py"]
    assert res.parked == [(f, check.UNSURE) for f in unsure]


RANKED = '''\
import os

QUERY = "x"


def small(a):
    return a


def big(a):
    b = a
    c = b
    d = c
    e = d
    f = e
    g = f
    return g


class K:
    @staticmethod
    def tiny():
        return 1
'''


def test_ranking_and_the_top_five_limit(proj):
    (proj / "app.py").write_text(RANKED)
    findings = {
        "high, small function": fnd("app.py", 7),
        "high, big function": fnd("app.py", 11),
        "high, module level, always fixed": fnd("app.py", 3, cwe="CWE-79", rule_id="r79"),
        "high, module level": fnd("app.py", 1, rule_id="r89"),
        "medium, decorated method": fnd("app.py", 21, severity="medium"),
        "medium, big function": fnd("app.py", 12, severity="medium"),
        "low, small function": fnd("app.py", 7, severity="low", rule_id="low"),
    }
    res = check.triage(proj, list(findings.values()))
    by_fp = {f.fingerprint: name for name, f in findings.items()}
    assert [by_fp[c.finding.fingerprint] for c in res.shown] == list(findings)[:5]
    assert [c.n for c in res.shown] == [1, 2, 3, 4, 5]
    assert [(by_fp[f.fingerprint], r) for f, r in res.parked] == [(n, check.LOWER) for n in list(findings)[5:]]
    text = check.format_text(res)
    assert "\n5. " in text and "\n6. " not in text and "2 ranked lower: show with --all" in text
    full = check.format_text(res, show_all=True)
    assert "--all" not in full and "app.py:12" in full and check.LOWER in full


def test_dismissal_hides_a_finding_and_lapses_when_the_line_changes(proj):
    (proj / "run.py").write_text("import subprocess\n\n\ndef go(cmd):\n    return subprocess.call(cmd, shell=True)\n")
    first = check.check_folder(proj)
    target = first.shown[0].finding
    assert target.line == 5
    with pytest.raises(IndexError):
        check.dismiss(proj, 0, "no such card")
    assert check.dismiss(proj, 1, "only ever called with a fixed string").fingerprint == target.fingerprint
    saved = json.loads((proj / ".aeropatch" / "dismissed.json").read_text(encoding="utf-8"))
    assert saved[target.fingerprint]["reason"] == "only ever called with a fixed string"
    assert saved[target.fingerprint]["date"]
    again = check.check_folder(proj)
    assert target.fingerprint not in [c.finding.fingerprint for c in again.shown]
    assert [(f.fingerprint, "fixed string" in r) for f, r in again.dismissed] == [(target.fingerprint, True)]
    assert "1 dismissed earlier" in check.format_text(again)
    (proj / "run.py").write_text("import subprocess\n\n\ndef go(command):\n    return subprocess.call(command, shell=True)\n")
    lapsed = check.check_folder(proj)
    assert lapsed.dismissed == [] and lapsed.shown[0].finding.line == 5


SECRETS = f'''\
DB_PASSWORD = "{SECRET}"


def connect(db):
    return db.login(user="app", password="{SECRET}")


def login(user, password="{SECRET}"):
    return user
'''


def _outputs(res) -> list[str]:
    return [check.format_text(res), check.format_text(res, show_all=True), check.write_html(res).read_text("utf-8"),
            (res.run_dir / "check.json").read_text("utf-8")]


def test_secret_value_appears_nowhere(proj):
    (proj / "settings.py").write_text(SECRETS)
    res = check.check_folder(proj)
    secrets = [c for c in res.shown if c.kind == "secret"]
    assert {c.finding.line for c in secrets} == {1, 5, 8}
    assert all(c.headline.startswith("If this is a real password or key") for c in secrets)
    assert "os.environ" in secrets[0].the_change
    outputs = _outputs(res)
    assert "settings.py:1" in outputs[0]
    for out in outputs:
        assert SECRET not in out


def test_a_lone_bandit_b105_shows_the_secrets_card(proj, monkeypatch):
    """B105-B107 come out at LOW severity: routed as secrets first, they are never set aside."""
    monkeypatch.setattr(scanners, "run_opengrep", lambda *a, **k: None)
    (proj / "config.py").write_text(f'api_password = "{SECRET}"\n')
    res = check.check_folder(proj)
    assert not res.opengrep and check.NO_OPENGREP in check.format_text(res)
    [card] = res.shown
    assert (card.kind, card.finding.rule_id, card.finding.severity) == ("secret", "B105", "low")
    assert card.finding.message == check.SECRET_MESSAGE
    assert 'os.environ["API_KEY"]' in card.the_change  # the two-line example, whichever card text is used
    for out in _outputs(res):
        assert SECRET not in out


def test_secret_on_the_line_without_a_bandit_secret_rule(proj):
    (proj / "hook.py").write_text(f'client = Client(url, api_key="{SECRET}")\n')
    res = check.triage(proj, [fnd("hook.py", 1, rule_id="aeropatch.python.ssrf-unvalidated-fetch", cwe="CWE-918")])
    assert res.shown[0].kind == "secret"
    assert SECRET not in check.render_html(res)


def test_html_escapes_finding_and_card_text(proj, tmp_path, monkeypatch):
    rule = {"headline": "Shows <b>hello</b> & \"quotes\"", "what_could_happen": "<i>x</i>",
            "when_it_matters": "a < b", "the_change": "it's > 0", "try_yourself": ["type <b>hello</b>"]}
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"version": 1, "rules": {"aeropatch.python.html-fstring-unescaped": rule}}))
    monkeypatch.setattr(check, "CARDS_PATH", cards)
    res = check.triage(proj, [fnd(message="<script>alert(1)</script>", rule_id="unknown-rule"),
                              fnd("b.py", rule_id="aeropatch.python.html-fstring-unescaped", cwe="CWE-79")])
    page = check.render_html(res)
    assert "<script" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<b>" not in page and "<i>" not in page
    for text in [*list(rule.values())[:4], rule["try_yourself"][0]]:
        assert html.escape(text) in page


def test_real_cards_render_escaped(proj, monkeypatch):
    """Every rule card in rules/cards.json loads and comes out escaped (the XSS card has a literal <b>)."""
    monkeypatch.setattr(check, "CARDS_PATH", config.ROOT / "rules" / "cards.json")
    cards = check.load_cards(check.CARDS_PATH)
    if not cards["rules"]:
        pytest.skip("rules/cards.json is not written yet")
    # B105-B107 findings get the secret card, so their own rule cards are never rendered.
    expected = {r: c for r, c in cards["rules"].items() if r not in check.SECRET_RULES} | {"B105": cards["secret"]}
    for r, card in expected.items():
        page = check.render_html(check.triage(proj, [fnd(rule_id=r, cwe="")]))
        for k in check.CARD_KEYS[:-1]:
            assert html.escape(card[k]) in page, (r, k)
        assert all(html.escape(t) in page for t in card["try_yourself"]), r
        assert "<b>" not in page, r


def test_missing_or_half_written_cards_give_generic_cards(proj, tmp_path, monkeypatch):
    res = check.triage(proj, [fnd(message="User input reaches SQL string formatting.")])
    [card] = res.shown
    assert card.generic and card.headline == check.GENERIC_CARD["headline"]
    text = check.format_text(res)
    assert "no plain-language note" in text and "The scanner says: User input reaches SQL string formatting." in text
    half = tmp_path / "half.json"
    half.write_text('{"version": 1, "rules": {"aeropatch.python.sqli-string-query": {"headline": "x"')
    assert check.load_cards(half) == check.load_cards(tmp_path / "missing.json")
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"rules": {"aeropatch.python.sqli-string-query": {"headline": "x"}}}))
    monkeypatch.setattr(check, "CARDS_PATH", incomplete)
    assert check.triage(proj, [fnd()]).shown[0].generic


def test_often_missed_note_only_on_generic_cards(proj, tmp_path, monkeypatch):
    rule = dict(check.GENERIC_CARD, headline="path card")
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"rules": {"aeropatch.python.path-traversal-open": rule}}))
    monkeypatch.setattr(check, "CARDS_PATH", cards)
    res = check.triage(proj, [fnd("a.py", rule_id="aeropatch.python.path-traversal-open", cwe="CWE-22"),
                              fnd("b.py", rule_id="aeropatch.python.unknown", cwe="CWE-918"),
                              fnd("c.py", rule_id="aeropatch.python.other", cwe="CWE-89")])
    assert {c.finding.path: c.note for c in res.shown} == {"a.py": "", "b.py": check.OFTEN_MISSED_NOTE, "c.py": ""}


def _same(f: Finding, want: Finding) -> bool:
    return f.rule_id == want.rule_id and f.path == want.path and abs(f.line - want.line) <= 3


@needs_opengrep
def test_scenario_finding_is_in_the_top_five():
    """Exit criterion 1 of part 3 §4: at least 25 of the 27 test scenarios."""
    ids = scenario.list_ids("test")
    misses = []
    for sid in ids:
        want = scenario.load(sid).finding
        res = check.check_folder(scenario.load(sid).repo_path)
        if not any(_same(c.finding, want) for c in res.shown):
            where = next((r for f, r in res.parked + res.dismissed if _same(f, want)), "not found by the scanners")
            misses.append(f"{sid}: {where}")
    hits = len(ids) - len(misses)
    print(f"\nscenario finding in the top five: {hits}/{len(ids)}", *misses, sep="\n  ")
    assert len(ids) == 27
    assert hits >= 25, misses
