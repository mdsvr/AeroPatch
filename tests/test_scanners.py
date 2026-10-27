"""The one-file re-scan with two hits of one rule (doc 17 part 2 §2, change 6). Runs Bandit on the host."""

from aeropatch.contracts import Finding
from aeropatch.tools import scanners

TWO = "def a(s):\n    return eval(s)\n\n\ndef b(s):\n    return eval(s)\n"


def test_fixing_one_of_two_hits_counts_as_fixed_only_with_a_start_count(tmp_path):
    (tmp_path / "app").mkdir()
    target = tmp_path / "app" / "calc.py"
    target.write_text(TWO, encoding="utf-8", newline="\n")
    finding = Finding(tool="bandit", rule_id="B307", path="app/calc.py", line=2)
    assert scanners.rule_hits(tmp_path, finding) == [2, 6]

    target.write_text(TWO.replace("return eval(s)", "return int(s)", 1), encoding="utf-8", newline="\n")
    assert scanners.rule_hits(tmp_path, finding) == [6]
    assert scanners.original_rule_present(tmp_path, finding, before=2) is False
    assert scanners.original_rule_present(tmp_path, finding) is True  # the any-hit answer earlier configs keep


def test_bandit_does_not_import_or_cache_modules_from_the_scanned_folder(tmp_path):
    """A json.py in the scanned folder must not shadow Bandit's own import (check writes nothing there)."""
    (tmp_path / "json.py").write_text("raise SystemExit('imported from the scanned folder')\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = eval(input())\n", encoding="utf-8")
    found = scanners.run_bandit(tmp_path)
    assert found is not None and any(f.rule_id == "B307" for f in found)
    assert not (tmp_path / "__pycache__").exists()
