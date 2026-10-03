"""Static part of training/inject_cwe.py: section parsing and the checks that need no sandbox."""

import importlib.util
import json

from aeropatch.config import ROOT

spec = importlib.util.spec_from_file_location("inject_cwe", ROOT / "training" / "inject_cwe.py")
inject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inject)

FIXED = 'def find(conn, name):\n    """Look a member up."""\n    return conn.execute("SELECT 1 WHERE ? = ?", (name, name))\n'
VULNERABLE = FIXED.replace('"SELECT 1 WHERE ? = ?", (name, name)', "f\"SELECT 1 WHERE '{name}' = '{name}'\"")
ANSWER = (f"Here you go.\n=== fixed ===\n```python\n{FIXED}```\n=== vulnerable ===\n{VULNERABLE}"
          "=== poc ===\ndef test_poc():\n    assert True\n=== regression ===\ndef test_ok():\n    assert True\n"
          "=== meta ===\nfunction: `find()`\ndescription: The name is formatted into the SQL text.\n")


def test_teacher_answer_becomes_a_scenario_directory(tmp_path):
    sections = inject.parse_sections(ANSWER)  # drops the code fence and the text before the first marker
    assert sections["fixed"] == FIXED and sections["vulnerable"] == VULNERABLE
    assert inject.write_example(tmp_path / "S-89-00001", "S-89-00001", "CWE-89", "library_loans", sections) == ""
    meta = json.loads((tmp_path / "S-89-00001" / "scenario.json").read_text())
    assert meta["target_function"] == "find" and meta["finding"]["line"] == 1 and meta["split"] == "train"
    patch = (tmp_path / "S-89-00001" / "reference_fix.patch").read_text()
    assert "+++ b/app/library_loans.py" in patch and '+    return conn.execute("SELECT 1 WHERE ? = ?"' in patch


def test_bad_answers_and_copied_eval_code_are_rejected_before_the_sandbox(tmp_path):
    sections = inject.parse_sections(ANSWER)

    def reject(**changed):
        return inject.write_example(tmp_path / "x", "x", "CWE-89", "m", {**sections, **changed})

    assert reject(poc="") == "format"
    assert reject(vulnerable="def find(:\n") == "syntax"
    assert reject(meta="function: other\n") == "no_target"
    assert reject(vulnerable=FIXED) == "injection_size"
    assert reject(vulnerable=VULNERABLE + "\n".join(f"x{i} = {i}" for i in range(11)) + "\n") == "injection_size"

    eval_code = (ROOT / "evaluations/scenarios/A-089-01/repo/app/db.py").read_text(encoding="utf-8")
    assert inject.ngrams(eval_code) & inject.ngrams("# copied\n" + eval_code)
    assert not inject.ngrams(eval_code) & inject.ngrams(VULNERABLE)
