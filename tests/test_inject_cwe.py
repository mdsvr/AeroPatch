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


def test_the_vulnerable_module_is_the_fixed_one_with_the_teachers_block_applied():
    block = ('<<<<<<< SEARCH\n    return conn.execute("SELECT 1 WHERE ? = ?", (name, name))\n=======\n'
             + VULNERABLE.splitlines()[-1] + "\n>>>>>>> REPLACE\n")
    sections = inject.parse_sections(f"=== fixed ===\n{FIXED}=== inject ===\n{block}=== poc ===\nx\n")
    assert inject.planted(sections, "app/m.py") == VULNERABLE
    assert inject.planted({**sections, "inject": block.replace("SELECT 1", "SELECT 2")}, "app/m.py") == ""  # not in the module
    assert inject.planted({**sections, "inject": block + block}, "app/m.py") == ""  # one block only
    assert inject.GIVEAWAY.search("    # no escaping here") and not inject.GIVEAWAY.search(VULNERABLE)


def test_wrong_tests_are_cut_out_of_a_test_file_and_helpers_stay():
    src = ("import pytest\n\n\ndef helper():\n    return 1\n\n\n@pytest.mark.parametrize('x', [1, 2])\n"
           "def test_wrong(x):\n    assert x == 0\n\n\ndef test_right():\n    assert helper() == 1\n")
    text, left = inject.drop_tests(src, {"test_wrong", "helper"})
    assert left == 1 and "test_wrong" not in text and "parametrize" not in text
    assert "def helper" in text and "def test_right" in text
    in_classes = "class TestA:\n    def test_a(self):\n        pass\n\n    def test_b(self):\n        pass\n\n\nclass TestB:\n    def test_c(self):\n        pass\n"
    assert inject.drop_tests(in_classes, {"test_a", "test_c"}) == ("class TestA:\n\n    def test_b(self):\n        pass\n\n\n", 1)
    assert inject.which_test("tests_poc.test_poc.test_x[http://127.0.0.1/x]") == ("poc", "test_x")
    assert inject.which_test("tests_regression.test_regression.TestA.test_poc_like") == ("regression", "test_poc_like")


def test_a_test_file_gets_the_imports_it_left_out_and_a_planted_comment_is_cut():
    test = "from app.m import find\n\n\ndef test_x(tmp_path):\n    conn = sqlite3.connect(':memory:')\n    add(conn)\n    with pytest.raises(ValueError):\n        find(conn, LIMIT)\n"
    module = "LIMIT = 3\n\n\ndef find(conn, name):\n    pass\n\n\ndef add(conn):\n    pass\n"
    assert inject.add_imports(test, "m", module).startswith("from app.m import LIMIT, add\nimport pytest\nimport sqlite3\nfrom app.m import find\n")
    block = ("<<<<<<< SEARCH\n    return conn.execute(\"SELECT 1 WHERE ? = ?\", (name, name))\n=======\n"
             "    # Missing bound parameters\n" + VULNERABLE.splitlines()[-1] + "  # formatted in\n>>>>>>> REPLACE\n")
    assert inject.planted({"fixed": FIXED, "inject": block}, "app/m.py") == VULNERABLE
    assert inject.GIVEAWAY.search('"""Looks a member up without any validation."""')


def test_a_method_can_be_the_target_and_is_named_with_its_class(tmp_path):
    def in_class(code):
        return "class Members:\n" + "".join(f"    {line}\n" for line in code.splitlines())

    sections = {**inject.parse_sections(ANSWER), "fixed": in_class(FIXED), "vulnerable": in_class(VULNERABLE)}
    assert inject.write_example(tmp_path / "S-89-00002", "S-89-00002", "CWE-89", "library_loans", sections) == ""
    meta = json.loads((tmp_path / "S-89-00002" / "scenario.json").read_text())
    assert meta["target_function"] == "Members.find" and meta["finding"]["line"] == 2


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
