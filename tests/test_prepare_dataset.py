"""training/prepare_dataset.py: the exclusion list, the fix-commit to SEARCH/REPLACE converter, the filters."""

import importlib.util
import json

import pytest

from aeropatch import scenario
from aeropatch.agent import prompts
from aeropatch.config import ROOT, SCENARIOS_DIR
from aeropatch.tools.context import get_context

spec = importlib.util.spec_from_file_location("prepare_dataset", ROOT / "training" / "prepare_dataset.py")
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)

PRE = '''\
import os

BASE = "/srv/files"


def read(name):
    path = os.path.join(BASE, name)
    with open(path) as f:
        return f.read()


def size(name):
    path = os.path.join(BASE, name)
    return os.path.getsize(path)
'''
CASES = {
    # `path = os.path.join(BASE, name)` is in the file twice: the block has to grow to be unique.
    "duplicate line": PRE.replace("    return os.path.getsize(path)", "    return os.stat(path).st_size"),
    "new lines that end blank": PRE.replace("def size", "def safe(name):\n    return name.isalnum()\n\n\ndef size"),
    "blank line removed": PRE.replace('BASE = "/srv/files"\n\n', 'BASE = "/srv/files"\n'),
    "first line": PRE.replace("import os", "import os.path"),
    "appended at the end": PRE + "\n\ndef exists(name):\n    return os.path.exists(os.path.join(BASE, name))\n",
    "two regions": PRE.replace("import os", "import os.path").replace("os.path.getsize(path)", "os.stat(path).st_size"),
    "whole body": PRE.replace("    with open(path) as f:\n        return f.read()", "    raise PermissionError(path)"),
}


@pytest.mark.parametrize("post", CASES.values(), ids=CASES.keys())
def test_a_fix_becomes_blocks_that_reapply_byte_exact(post):
    target = prep.convert(PRE, post, "app/files.py", "Path traversal in read.  It joins the name unchecked. Third.")
    assert target.startswith("RATIONALE: Path traversal in read. It joins the name unchecked.\n<<<<<<< SEARCH app/files.py\n")
    assert prep.reapplies(PRE, post, "app/files.py", target)
    assert not prep.reapplies(PRE, post + "\n", "app/files.py", target)  # byte-exact, not "close"


def test_two_far_regions_are_two_blocks_and_a_divider_line_cannot_be_converted():
    assert prep.convert(PRE, CASES["two regions"], "a.py", "x").count("<<<<<<< SEARCH") == 2
    # edits.parse reads a line of equals signs in SEARCH as the divider: a fix that changes one has no target,
    # and a fix beside one is a block without context.
    assert prep.convert("Title\n=======\nold\n", "Title\n-------\nold\n", "a.py", "x") is None
    assert prep.convert("Title\n=======\nold\n", "Title\n=======\nnew\n", "a.py", "x").endswith("SEARCH a.py\nold\n=======\nnew\n>>>>>>> REPLACE")
    # apply_one trims blank lines off a block's ends, so a fix that drops the final newline has none either.
    assert prep.convert(PRE, PRE.rstrip("\n"), "a.py", "x") is None


def test_a_block_has_to_be_copyable_from_what_the_prompt_shows():
    post = PRE.replace("def size(name):", "def size(name: str):")
    shown = PRE[PRE.index("def size"):].rstrip("\n")  # a long file is shown as the one function
    # The line above the change is out of view, so the block that works is the one without context.
    assert "\n<<<<<<< SEARCH app/files.py\ndef size(name):\n=======\ndef size(name: str):\n" in prep.convert(PRE, post, "app/files.py", "x", shown)
    assert "        return f.read()\n\n\ndef size(name):\n    path" in prep.convert(PRE, post, "app/files.py", "x")
    assert prep.convert(PRE, post, "app/files.py", "x", "import os") is None


def test_a_git_patch_is_applied_only_where_it_sits():
    patch = ("diff --git a/app/files.py b/app/files.py\nindex 1a..2b 100644\n--- a/app/files.py\n+++ b/app/files.py\n"
             "@@ -12,3 +12,3 @@ def read(name):\n def size(name):\n-    path = os.path.join(BASE, name)\n"
             "+    path = os.path.join(BASE, os.path.basename(name))\n     return os.path.getsize(path)\n")
    part = prep.split_patch(patch)["app/files.py"]
    assert prep.apply_patch(PRE, part) == PRE.replace("size(name):\n    path = os.path.join(BASE, name)",
                                                      "size(name):\n    path = os.path.join(BASE, os.path.basename(name))")
    assert prep.apply_patch(PRE, part.replace("-12,3", "-6,3")) is None  # `def read` is there, not `def size`
    assert prep.apply_patch(PRE, part + "\\ No newline at end of file\n") is None


def test_the_filters_read_a_fix_as_the_plan_describes_it():
    post = PRE.replace("import os", "import os\nimport stat").replace("os.path.getsize(path)", "os.stat(path)[stat.ST_SIZE]")
    assert prep.finding_line(PRE, post) == 14  # the changed line of `size`, not the import added on line 2
    assert prep.functions_touched(PRE, post) == 1 and not prep.noisy(PRE, post)
    assert prep.noisy(PRE, PRE.replace("return f.read()", "return  f.read()"))  # whitespace only
    assert prep.grams("total = price * count", 5, blank=True) == prep.grams("s = a * b", 5, blank=True)
    assert prep.grams("total = price * count", 5) != prep.grams("s = a * b", 5)
    # The runs that touch a benchmark fix line: all of a text's runs when every line counts, none for a line it lacks.
    assert prep.runs_on(PRE, set(range(20))) == prep.grams(PRE, 13) > prep.runs_on(PRE, {13}) > prep.runs_on(PRE, {99}) == set()
    # SWE-smith names its copy of a repository "owner__name.commit": the exclusion list has to see through it.
    assert prep.excluded(prep.smith_repo("swesmith/andialbrecht__sqlparse.e57923b3"))
    assert not prep.excluded(prep.smith_repo("swesmith/getnikola__nikola.0f4c230e"))


def test_the_prompt_of_an_example_is_the_prompt_the_loop_sends():
    """doc 09 §5: built by the same functions, from a copy of the file in an empty directory."""
    task = scenario.load("C-328-01")
    f = task.finding
    it = {"id": task.id, "cwe": task.cwe, "path": f.path, "line": f.line, "tool": f.tool, "rule": f.rule_id,
          "message": f.message, "description": task.description, "pre": (task.repo_path / f.path).read_text(encoding="utf-8")}
    ctx = get_context(task.repo_path, f.path, f.line, task.allowed_paths)
    shown, prompt, function = prep.rendered(it)
    assert (shown, prompt) == (ctx.files[f.path], prompts.first_user_message(task, ctx))
    assert function.startswith("def hash_password(") and function in shown


def test_no_benchmark_project_can_enter_the_training_data():
    tier_b = json.loads((SCENARIOS_DIR / "split.json").read_text(encoding="utf-8"))["test_b"]
    repos = {prep.COMMIT_RE.match(json.loads((SCENARIOS_DIR / sid / "scenario.json").read_text(encoding="utf-8"))
                                  ["fix_commit"])[1] for sid in tier_b}
    assert all(prep.excluded(repo) for repo in repos) and len(repos) == len(prep.EXCLUDED)
    assert prep.excluded("someone/fork", "PyJWT") and prep.excluded("etingof/pyasn1.git".removesuffix(".git"))
    assert not prep.excluded("pallets/flask", "Flask")
    assert prep.is_test("tests/unit/test_x.py") and prep.is_test("pkg/conftest.py") and not prep.is_test("pkg/attest.py")
    assert prep.is_doc("CHANGES.rst") and prep.is_doc("docs/api.md") and not prep.is_doc("pkg/history.py")
