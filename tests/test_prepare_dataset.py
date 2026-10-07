"""training/prepare_dataset.py: the exclusion list and the fix-commit to SEARCH/REPLACE converter."""

import importlib.util
import json

import pytest

from aeropatch.config import ROOT, SCENARIOS_DIR

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
    # edits.parse reads a line of equals signs as the SEARCH/REPLACE divider, so this fix has no target.
    assert prep.convert("Title\n=======\nold\n", "Title\n=======\nnew\n", "a.py", "x") is None
    # apply_one trims blank lines off a block's ends, so a fix that drops the final newline has none either.
    assert prep.convert(PRE, PRE.rstrip("\n"), "a.py", "x") is None


def test_no_benchmark_project_can_enter_the_training_data():
    tier_b = json.loads((SCENARIOS_DIR / "split.json").read_text(encoding="utf-8"))["test_b"]
    repos = {prep.COMMIT_RE.match(json.loads((SCENARIOS_DIR / sid / "scenario.json").read_text(encoding="utf-8"))
                                  ["fix_commit"])[1] for sid in tier_b}
    assert all(prep.excluded(repo) for repo in repos) and len(repos) == len(prep.EXCLUDED)
    assert prep.excluded("someone/fork", "PyJWT") and prep.excluded("etingof/pyasn1.git".removesuffix(".git"))
    assert not prep.excluded("pallets/flask", "Flask")
    assert prep.is_test("tests/unit/test_x.py") and prep.is_test("pkg/conftest.py") and not prep.is_test("pkg/attest.py")
    assert prep.is_doc("CHANGES.rst") and prep.is_doc("docs/api.md") and not prep.is_doc("pkg/history.py")
