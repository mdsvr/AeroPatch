"""Phase B of reports/Real bug detection and model mix.md: the extra rules (each fires on its seeded
fixture and not on its fixed twin), the ReDoS checker and the advisory lookup. No network."""

import json
import urllib.error
from pathlib import Path

import pytest

from aeropatch import check
from aeropatch.contracts import Finding
from aeropatch.tools import advisories, redos, scanners

FIXTURES = Path(__file__).parent / "fixtures" / "extra_rules"
needs_opengrep = pytest.mark.skipif(scanners.opengrep_binary() is None, reason="opengrep/semgrep not installed")
SEEDED = {"header-injection": [9, 15], "path-traversal-taint": [12, 18], "code-injection-taint": [9],
          "decompression-bomb": [10], "unbounded-body-read": [6], "jwt-decode-unverified": [7, 11, 15, 20]}


@needs_opengrep
@pytest.mark.parametrize("rule", sorted(SEEDED))
def test_extra_rule_fires_on_its_seeded_case_and_not_on_its_fixed_twin(rule):
    found = scanners.run_opengrep(FIXTURES / rule, extra=True) or []
    mine = [f for f in found if f.rule_id == f"aeropatch.extra.{rule}"]
    assert sorted(f.line for f in mine if f.path == "bad.py") == SEEDED[rule]
    assert not [f for f in mine if f.path == "good.py"]


@needs_opengrep
def test_extra_rules_stay_out_of_the_default_scan_and_their_rescan_uses_them():
    folder = FIXTURES / "code-injection-taint"
    assert not [f for f in scanners.run_opengrep(folder) or [] if f.rule_id.startswith(scanners.EXTRA_PREFIX)]
    finding = Finding(tool="opengrep", rule_id="aeropatch.extra.code-injection-taint", path="bad.py", line=9)
    assert scanners.rule_hits(folder, finding) == [9]


def test_redos_flags_a_nested_quantifier_and_not_its_rewrite(tmp_path):
    (tmp_path / "a.py").write_text('import re\nGOOD = re.compile(r"^[A-Za-z]+(?:\\s+[A-Za-z]+)*$")\n'
                                   'BAD = re.compile(r"^([A-Za-z]+\\s*)+$")\nTEXT = "not a regex"\n',
                                   encoding="utf-8")
    assert [(f.line, f.tool, f.cwe) for f in redos.scan(tmp_path, ["a.py"])] == [(3, "regexploit", "CWE-1333")]


def test_read_pins_takes_exact_pins_only(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "Flask==2.0.0  # web\nrequests>=2\nPyJWT[crypto] == 2.3.0 ; python_version >= '3.8'\n-r other.txt\n"
        "flask==2.0.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\ndependencies = [\n  "mako==1.2.1",\n'
                                             '  "click",\n]\n', encoding="utf-8")
    pins = advisories.read_pins(tmp_path)
    assert [(p.name, p.version, p.path, p.line) for p in pins] == [
        ("flask", "2.0.0", "requirements.txt", 1), ("pyjwt", "2.3.0", "requirements.txt", 3),
        ("mako", "1.2.1", "pyproject.toml", 4)]


def _vuln(vid, cve, fixed):
    return {"id": vid, "aliases": [cve], "summary": f"{vid} summary",
            "affected": [{"package": {"name": "PyJWT", "ecosystem": "PyPI"},
                          "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, *fixed]}]}]}


def test_audit_names_the_lowest_version_that_fixes_every_advisory(tmp_path):
    (tmp_path / "requirements.txt").write_text("pyjwt==2.3.0\nclick==8.1.7\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("import jwt\n", encoding="utf-8")
    vulns = {"GHSA-1": _vuln("GHSA-1", "CVE-2022-29217", [{"fixed": "2.4.0"}]),
             "GHSA-2": _vuln("GHSA-2", "CVE-2026-1", [{"fixed": "1.7.2"}, {"introduced": "2.0"}, {"fixed": "2.10.1"}]),
             "GHSA-3": _vuln("GHSA-3", "CVE-2026-2", [])}  # no fix published
    sent = []

    def post(url, body):
        sent.append(body)
        return {"results": [{"vulns": [{"id": "GHSA-1"}, {"id": "GHSA-2"}, {"id": "GHSA-3"}]}, {}]}

    adv, n, err = advisories.audit(tmp_path, ["app.py"], post=post, get=lambda url: vulns[url.rsplit("/", 1)[1]])
    assert (n, err) == (2, "")
    assert json.dumps(sent).count('"version"') == 2 and "import jwt" not in json.dumps(sent)  # no code sent
    [a] = adv
    assert (a.pin.name, a.ids, a.fixed, a.unfixed, a.imported_in) == (
        "pyjwt", ["CVE-2022-29217", "CVE-2026-1", "CVE-2026-2"], "2.10.1", ["CVE-2026-2"], ["app.py"])
    assert "No newer version fixes CVE-2026-2 yet" in dict(check.advisory_fields(a))["What the change does"]


def test_audit_reports_nothing_when_the_lookup_fails(tmp_path):
    (tmp_path / "requirements.txt").write_text("pyjwt==2.3.0\n", encoding="utf-8")

    def post(url, body):
        raise urllib.error.URLError("offline")

    adv, n, err = advisories.audit(tmp_path, [], post=post)
    assert adv == [] and n == 1 and "did not answer" in err


def test_check_shows_an_advisory_card_and_offline_skips_the_lookup(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("pyjwt==2.3.0\n", encoding="utf-8")
    pin = advisories.Pin("pyjwt", "2.3.0", "requirements.txt", 1)
    fake = advisories.Advisory(pin=pin, ids=["CVE-2022-29217"], summary="Key confusion", fixed="2.4.0")
    monkeypatch.setattr(advisories, "audit", lambda folder, py: ([fake], 1, ""))
    monkeypatch.setattr(check.config, "RUNS_DIR", tmp_path / "runs")
    res = check.check_folder(tmp_path)
    text = check.format_text(res)
    assert "change pyjwt==2.3.0 to pyjwt==2.4.0" in text and "osv.dev" in text
    assert "pyjwt==2.4.0" in check.render_html(res)
    monkeypatch.setattr(advisories, "audit", lambda *a: pytest.fail("looked up while offline"))
    assert check.check_folder(tmp_path, offline=True).advisories == []
