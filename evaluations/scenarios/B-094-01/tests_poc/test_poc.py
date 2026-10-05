import pytest

import sqlparse


def _run_generated_snippet(sql_text):
    """Execute the Python snippet that sqlparse generates for `sql_text`, as its user would."""
    marker = []
    namespace = {"MARKER": marker}
    try:
        exec(sqlparse.format(sql_text, output_format="python"), namespace)
    except SyntaxError:
        return marker, None
    return marker, namespace.get("sql")


@pytest.mark.parametrize("sql_text", [
    "x\\' + str(MARKER.append(1)) #",
    "select 'a' -- x\\' + str(MARKER.append(1)) #",
])
def test_sql_text_cannot_run_code_in_the_generated_snippet(sql_text):
    marker, _ = _run_generated_snippet(sql_text)
    assert marker == []


@pytest.mark.parametrize("sql_text", [
    "select '\\foo\\'",
    "select * from t where name = 'x\\'",
    "select 'C:\\temp\\file' from t",
])
def test_generated_snippet_holds_exactly_the_sql_text(sql_text):
    _, value = _run_generated_snippet(sql_text)
    assert value == sql_text
