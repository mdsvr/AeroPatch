"""Output-format tests from sqlparse's own tests/test_format.py (class TestOutputFormat)."""
import sqlparse


def test_python():
    sql = "select * from foo;"
    assert sqlparse.format(sql, output_format="python") == "sql = 'select * from foo;'"
    assert sqlparse.format(sql, output_format="python", reindent=True) == "\n".join([
        "sql = ('select * '",
        "       'from foo;')"])


def test_python_multiple_statements():
    sql = "select * from foo; select 1 from dual"
    assert sqlparse.format(sql, output_format="python") == "\n".join([
        "sql = 'select * from foo; '",
        "sql2 = 'select 1 from dual'"])


def test_python_quotes_are_escaped():
    assert sqlparse.format("select 'it''s' from t", output_format="python") == "sql = 'select \\'it\\'\\'s\\' from t'"
    assert sqlparse.format('select "dq" from t', output_format="python") == "sql = 'select \"dq\" from t'"


def test_python_snippet_evaluates_to_the_sql_text():
    for sql in ("select 'plain' from t where a = 1", "select 'it''s', \"x\" from t -- note",
                "insert into t values (1, 'a b')"):
        namespace = {}
        exec(sqlparse.format(sql, output_format="python"), namespace)
        assert namespace["sql"] == sql


def test_php():
    sql = "select * from foo;"
    assert sqlparse.format(sql, output_format="php") == '$sql = "select * from foo;";'
    assert sqlparse.format(sql, output_format="php", reindent=True) == "\n".join([
        '$sql  = "select * ";',
        '$sql .= "from foo;";'])


def test_sql_output_format_changes_nothing():
    sql = "select * from foo;"
    assert sqlparse.format(sql, output_format="sql") == "select * from foo;"
