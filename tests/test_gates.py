"""One passing and one failing example per gate rule (doc 08 part 2, §2)."""

import pytest

from aeropatch.agent.gates import check

ORIG = {"app/db.py": "import sqlite3\n\n\ndef find(conn, n):\n    return conn.execute('q', (n,))\n\n\nclass Repo:\n    def get(self):\n        return 1\n"}
ALLOWED = ["app/db.py"]


def change(new, path="app/db.py", orig=ORIG):
    return check(orig, {path: new}, ALLOWED)


GOOD = ORIG["app/db.py"].replace("'q'", "'q2'")


def test_good_edit_passes():
    r = change(GOOD)
    assert r.ok, r.details


@pytest.mark.parametrize("path", ["tests/test_db.py", "conftest.py", "requirements.txt", ".github/x.yml",
                                  "pyproject.toml", "Dockerfile", ".env"])
def test_forbidden_path(path):
    r = check({path: "a = 1\n"}, {path: "a = 2\n"}, ALLOWED + [path])
    assert "FORBIDDEN_PATH" in r.violations


def test_forbidden_path_ok_for_app_file():
    assert "FORBIDDEN_PATH" not in change(GOOD).violations


def test_out_of_scope():
    r = check({"app/other.py": "a = 1\n"}, {"app/other.py": "a = 2\n"}, ALLOWED)
    assert "OUT_OF_SCOPE" in r.violations
    assert "OUT_OF_SCOPE" not in change(GOOD).violations


def test_too_large():
    big = GOOD + "".join(f"X{i} = {i}\n" for i in range(70))
    assert "TOO_LARGE" in change(big).violations
    assert "TOO_LARGE" not in change(GOOD).violations


def test_syntax_error():
    assert "SYNTAX_ERROR" in change(GOOD + "def broken(:\n").violations
    assert "SYNTAX_ERROR" not in change(GOOD).violations


def test_deletes_symbol():
    assert "DELETES_SYMBOL" in change(GOOD.split("class Repo")[0]).violations
    assert "DELETES_SYMBOL" not in change(GOOD).violations


def test_suppresses_checks():
    assert "SUPPRESSES_CHECKS" in change(GOOD.replace("('q2', (n,))", "('q2', (n,))  # nosec")).violations
    assert "SUPPRESSES_CHECKS" not in change(GOOD).violations


def test_risky_import():
    assert "RISKY_IMPORT" in change("import subprocess\n" + GOOD).violations
    assert "RISKY_IMPORT" in change(GOOD + "\nZ = eval('1')\n").violations
    assert "RISKY_IMPORT" in change("from urllib.request import urlopen\n" + GOOD).violations
    assert "RISKY_IMPORT" not in change("import re\n" + GOOD).violations
    assert "RISKY_IMPORT" not in change("from urllib.parse import urlparse\n" + GOOD).violations


def test_risky_import_allowlisted_per_scenario():
    r = check(ORIG, {"app/db.py": "import subprocess\n" + GOOD}, ALLOWED, allow_imports=["subprocess"])
    assert "RISKY_IMPORT" not in r.violations


def test_no_change():
    assert "NO_CHANGE" in change(ORIG["app/db.py"]).violations
    assert "NO_CHANGE" not in change(GOOD).violations
