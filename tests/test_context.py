import shutil
from pathlib import Path

import pytest

from aeropatch.tools.context import function_span, get_context

FIX = Path(__file__).parent / "fixtures" / "context"


@pytest.fixture
def repo(tmp_path):
    shutil.copytree(FIX, tmp_path / "repo")
    return tmp_path / "repo"


def test_plain_function_has_imports_constants_and_callers(repo):
    ctx = get_context(repo, "sample.py", 11)
    text = ctx.files["sample.py"]
    assert ctx.target == "outer"
    assert "import os" in text and 'BASE = Path("/srv/files")' in text
    assert "LIMIT = 10" not in text  # not referenced by outer
    assert "call sites" in text and 'return outer("a")' in text
    assert ctx.token_count < 3000


def test_nested_function_returns_outer_scope(repo):
    ctx = get_context(repo, "sample.py", 10)
    assert ctx.target == "outer.inner"
    assert "def outer(name):" in ctx.files["sample.py"]


def test_decorated_method_includes_decorator_class_header_and_signatures(repo):
    ctx = get_context(repo, "sample.py", 26)
    text = ctx.files["sample.py"]
    assert ctx.target == "Store.load"
    assert "@staticmethod" in text and "class Store:" in text
    assert "def __init__(self, root): ..." in text
    assert "return data.strip()" in text


def test_no_line_number_prefixes(repo):
    text = get_context(repo, "sample.py", 11).files["sample.py"]
    code_lines = [line for line in text.splitlines() if not line.startswith("#")]
    assert not any(line[:4].strip().isdigit() for line in code_lines if line.strip())


def test_syntax_error_file_still_gives_context(repo):
    ctx = get_context(repo, "broken.py", 5)
    assert ctx.target == "ok"
    assert "json.loads" in ctx.files["broken.py"]


def test_function_span():
    src = (FIX / "sample.py").read_text()
    assert function_span(src, "Store.load") == (25, 27)
    assert function_span(src, "outer") == (8, 11)
    assert function_span(src, "missing") is None
