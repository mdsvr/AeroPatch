import pytest

from aeropatch.agent import edits
from aeropatch.contracts import Edit

SRC = """import sqlite3


def find_user(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name = '%s'" % name)
    return cur.fetchall()


def count(conn):
    cur = conn.cursor()
    return cur.fetchone()
"""


def block(path, search, replace):
    return f"<<<<<<< SEARCH {path}\n{search}\n=======\n{replace}\n>>>>>>> REPLACE"


def test_parse_rationale_blocks_and_trailing_text_ignored():
    text = "<think>hmm</think>RATIONALE: bind it.\n" + block("a.py", "x = 1", "x = 2") + "\nextra chatter"
    p = edits.parse(text)
    assert p.parse_error == ""
    assert p.rationale == "bind it."
    assert p.edits == [Edit("a.py", "x = 1", "x = 2")]


def test_parse_unterminated_and_empty():
    assert "unterminated" in edits.parse("<<<<<<< SEARCH a.py\nx\n=======\ny").parse_error
    assert "no SEARCH" in edits.parse("just prose").parse_error


def test_exact_match():
    e = Edit("db.py", '    cur.execute("SELECT id FROM users WHERE name = \'%s\'" % name)',
             '    cur.execute("SELECT id FROM users WHERE name = ?", (name,))')
    out = edits.apply_one(SRC, e)
    assert '(name,))' in out and "%s" not in out


def test_whitespace_tolerant_match_keeps_file_indentation():
    e = Edit("db.py", 'cur.execute("SELECT id FROM users WHERE name = \'%s\'" % name)   \nreturn cur.fetchall()',
             'cur.execute("SELECT id FROM users WHERE name = ?", (name,))\nreturn cur.fetchall()')
    out = edits.apply_one(SRC, e)
    assert '    cur.execute("SELECT id FROM users WHERE name = ?", (name,))\n    return cur.fetchall()' in out


def test_not_found_gives_closest_lines():
    e = Edit("db.py", '    cur.execute("SELECT id FROM user WHERE name = " + name)', "x")
    with pytest.raises(edits.ApplyError) as ei:
        edits.apply_one(SRC, e)
    assert ei.value.code == "SEARCH_NOT_FOUND"
    assert "Closest lines" in ei.value.message


def test_ambiguous():
    with pytest.raises(edits.ApplyError) as ei:
        edits.apply_one(SRC, Edit("db.py", "    cur = conn.cursor()", "    cur = conn.cursor()  # x"))
    assert ei.value.code == "SEARCH_AMBIGUOUS"


def test_multiple_blocks_in_one_file_and_across_two_files():
    files = {"db.py": SRC, "b.py": "A = 1\nB = 2\n"}
    changed = edits.apply_edits(files, [
        Edit("db.py", "def count(conn):", "def count(conn, table):"),
        Edit("db.py", "    return cur.fetchone()", "    return cur.fetchone()[0]"),
        Edit("b.py", "B = 2", "B = 3"),
    ])
    assert "def count(conn, table):" in changed["db.py"] and "fetchone()[0]" in changed["db.py"]
    assert changed["b.py"] == "A = 1\nB = 3\n"


def test_unknown_file_rejected():
    with pytest.raises(edits.ApplyError) as ei:
        edits.apply_edits({"a.py": "x"}, [Edit("new.py", "x", "y")])
    assert ei.value.code == "UNKNOWN_FILE"


def test_normalized_hash_ignores_indent():
    a = [Edit("a.py", "    x = 1", "    x = 2")]
    b = [Edit("a.py", "x = 1", "x = 2")]
    assert edits.normalized_hash(a) == edits.normalized_hash(b)
