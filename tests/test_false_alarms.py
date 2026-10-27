"""Known false-alarm shapes are set aside, and the dangerous form of each is kept (point 2)."""

import pytest

from aeropatch import false_alarms
from aeropatch.contracts import Finding

CASES = [
    # (rule, code, line, set aside?)
    ("aeropatch.python.sqli-string-query", "def f(c):\n    c.execute('VACUUM')\n", 2, True),
    ("aeropatch.python.sqli-string-query", "def f(c, x):\n    c.execute(f'SELECT {x}')\n", 2, False),
    ("aeropatch.python.sqli-string-query",
     "def f(c, ids):\n    ph = ', '.join(['?'] * len(ids))\n    c.execute(f'SELECT * WHERE id IN ({ph})', ids)\n", 3, True),
    ("aeropatch.python.sqli-string-query",
     "def f(c, ids, name):\n    ph = ', '.join(['?'] * len(ids))\n    c.execute(f'SELECT {name} WHERE id IN ({ph})')\n", 3, False),
    ("aeropatch.python.sqli-string-query",
     "def drop(db, t):\n    db.execute(f'DROP TABLE {quote_identifier(t.name)}')\n", 2, True),
    ("aeropatch.python.sqli-string-query",
     "def ren(db, a, b):\n    db.execute(f'ALTER TABLE {quote_identifier(a)} RENAME TO {quote_identifier(b)}')\n", 2, True),
    ("aeropatch.python.sqli-string-query",  # urllib's quote is not SQL quoting
     "from urllib.parse import quote\ndef f(db, t):\n    db.execute(f'DROP TABLE {quote(t)}')\n", 3, False),
    ("aeropatch.python.sqli-string-query",  # one quoted name does not cover a raw value beside it
     "def f(db, t, v):\n    db.execute(f\"SELECT * FROM {quote_identifier(t)} WHERE a = '{v}'\")\n", 2, False),
    ("aeropatch.python.subprocess-shell", "import os\nos.system('pybabel compile -d app/translations')\n", 2, True),
    ("aeropatch.python.subprocess-shell", "import os\ndef f(lang):\n    os.system('pybabel init -l ' + lang)\n", 3, False),
    ("B105", "def f(password):\n    if password == '':\n        return False\n", 2, True),
    ("B105", "def f(t):\n    if t == 'your_access_token':\n        return False\n", 2, True),
    ("B105", "def f(k):\n    if k == 'sk-Live9xQ2'\n", 2, None),  # does not parse: kept
    ("B105", "def f(k):\n    if k == 'sk-Live9xQ2':\n        return 1\n", 2, False),
    ("aeropatch.python.hardcoded-credential", "token_type = 'bearer'\n", 1, True),
    # A real Flask key with a space in it (fresh repos, 2026-10-27): no "it is a message" shape.
    ("aeropatch.python.hardcoded-credential", "SECRET_KEY = 'my precious'\n", 1, False),
    ("aeropatch.python.hardcoded-credential", "secret = 'secret123'\n", 1, False),
    # Weak hashes are all kept: vulnpy's deliberate MD5 sinks name no password either.
    ("B324", "import hashlib\ndef gravatar_hash(email):\n    return hashlib.md5(email.encode()).hexdigest()\n", 3, False),
    ("aeropatch.python.tar-extract-unfiltered",
     "import zipfile\ndef f(p, d):\n    z = zipfile.ZipFile(p)\n    z.extractall(d)\n", 4, True),
    ("aeropatch.python.tar-extract-unfiltered",
     "import tarfile\ndef f(p, d):\n    t = tarfile.open(p)\n    t.extractall(d)\n", 4, False),
    ("aeropatch.python.url-prefix-allowlist",
     "def fetch(symbol):\n    if symbol.startswith('NSE:') or symbol.startswith('BSE:'):\n        return 1\n", 2, True),
    ("aeropatch.python.url-prefix-allowlist",
     "def fetch(url):\n    if url.startswith('https://cdn.example'):\n        return 1\n", 2, False),
]


@pytest.mark.parametrize(("rule", "code", "line", "aside"), CASES)
def test_false_alarm_shapes(tmp_path, rule, code, line, aside):
    (tmp_path / "app.py").write_text(code, encoding="utf-8")
    why = false_alarms.reason(tmp_path, Finding(tool="opengrep", rule_id=rule, path="app.py", line=line), {})
    assert (why is not None) is bool(aside), why
