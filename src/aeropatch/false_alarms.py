"""Known false-alarm shapes, set aside in `check` before the five are cut (point 2 of the plan
after reports/Real bug detection and model mix.md).

On 14 real repositories (2026-10-26) 31 of 42 shown findings were false, and most came from a few
shapes of code that a scanner rule cannot tell apart from the dangerous form. Each check here reads
the flagged statement with `ast` and answers one question about it; anything it cannot read is kept.
A set-aside finding stays listed with `--all`, with the reason.

The rules in rules/ are not changed: their re-scan decides the labels of every measured config.
Two shapes were tried and dropped after the fresh repos (2026-10-27) showed them hiding real
findings: "a credential-named string with a space is a message" (a Flask SECRET_KEY 'my precious')
and "a weak hash whose names mention no password is harmless" (vulnpy's deliberate MD5 sinks).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from aeropatch.contracts import Finding

SQL_RULES = {"aeropatch.python.sqli-string-query", "B608"}
SHELL_RULES = {"aeropatch.python.subprocess-shell", "B602", "B605"}
SECRET_LIKE_RULES = {"aeropatch.python.hardcoded-credential", "B105", "B106", "B107"}
ARCHIVE_RULES = {"aeropatch.python.tar-extract-unfiltered", "B202"}
URL_PREFIX_RULES = {"aeropatch.python.url-prefix-allowlist"}

PLACEHOLDER = re.compile(r"^[a-z_ ]*$")  # lower-case words: "your_access_token", ""
TOKEN_TYPES = {"bearer", "token", "basic", "digest", "jwt", "oauth"}


class _File:
    """One parsed file, for the statement and the function around a line."""

    def __init__(self, path: Path):
        self.text = path.read_text(encoding="utf-8", errors="replace")
        self.tree = ast.parse(self.text)

    def statement(self, line: int) -> ast.stmt | None:
        best = None
        for n in ast.walk(self.tree):
            if isinstance(n, ast.stmt) and n.lineno <= line <= (n.end_lineno or n.lineno) and (
                    best is None or (n.end_lineno - n.lineno) <= (best.end_lineno - best.lineno)):
                best = n
        return best

    def function_name(self, line: int) -> str:
        names = [n.name for n in ast.walk(self.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.lineno <= line <= n.end_lineno]
        return names[-1] if names else ""


def _text(node) -> str | None:
    """A string written out in full: a literal, or an f-string with no {placeholders}."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and all(isinstance(v, ast.Constant) for v in node.values):
        return "".join(v.value for v in node.values)
    return None


def _calls_on(stmt: ast.stmt, line: int, names: set[str]) -> list[ast.Call]:
    out = []
    for n in ast.walk(stmt):
        if isinstance(n, ast.Call) and n.lineno <= line <= n.end_lineno:
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            if name in names:
                out.append(n)
    return out


def _fixed_first_arg(calls: list[ast.Call]) -> bool:
    return bool(calls) and all(c.args and _text(c.args[0]) is not None for c in calls)


QMARKS = re.compile(r"""^\s*['"],\s*['"]\.join\(\s*\[\s*['"]\?['"]\s*\]\s*\*""")


# Functions that quote an SQL identifier (a table or column name), so a value passed through one
# cannot end the name and start new SQL. Added 2026-10-27 from sqlite-utils, where every one of
# its 5 shown SQL findings was an f-string of quote_identifier(...) calls: the fresh repos are
# spent as evidence for this shape. Plain `quote` is left out: urllib's quote is not SQL quoting.
IDENTIFIER_QUOTERS = {"quote_identifier", "quote_ident", "quote_name", "escape_identifier", "quote_column",
                      "quote_table"}


def _only_placeholders(arg, src: _File, line: int) -> bool:
    """An f-string whose every {...} is a name set, in the same function, to ', '.join(['?'] * n),
    or a call to an SQL identifier-quoting function."""
    if not isinstance(arg, ast.JoinedStr):
        return False
    values = [v.value for v in arg.values if isinstance(v, ast.FormattedValue)]
    if not values:
        return False
    fn = [n for n in ast.walk(src.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
          and n.lineno <= line <= n.end_lineno]
    scope = fn[-1] if fn else src.tree
    bound = {t.id: ast.get_source_segment(src.text, n.value) or "" for n in ast.walk(scope)
             if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}

    def safe(v) -> bool:
        if isinstance(v, ast.Name):
            return bool(QMARKS.match(bound.get(v.id, "")))
        if isinstance(v, ast.Call):
            f = v.func
            return (f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")) in IDENTIFIER_QUOTERS
        return False
    return all(safe(v) for v in values)


def _zip_names(tree: ast.AST) -> set[str]:
    """Names bound to a ZipFile: `z = ZipFile(...)`, `with zipfile.ZipFile(...) as z`."""
    def is_zip(call):
        return isinstance(call, ast.Call) and (getattr(call.func, "attr", None) == "ZipFile"
                                               or getattr(call.func, "id", None) == "ZipFile")
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and is_zip(n.value):
            names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        elif isinstance(n, ast.withitem) and is_zip(n.context_expr) and isinstance(n.optional_vars, ast.Name):
            names.add(n.optional_vars.id)
    return names


def reason(folder: Path, f: Finding, cache: dict) -> str | None:
    """Why this finding is very likely a false alarm, or None to keep it."""
    rules = SQL_RULES | SHELL_RULES | SECRET_LIKE_RULES | ARCHIVE_RULES | URL_PREFIX_RULES
    if f.rule_id not in rules:
        return None
    if f.path not in cache:
        try:
            cache[f.path] = _File(folder / f.path)
        except (OSError, SyntaxError, ValueError, RecursionError):
            cache[f.path] = None
    src = cache[f.path]
    stmt = src.statement(f.line) if src else None
    if stmt is None:
        return None

    if f.rule_id in SQL_RULES:
        calls = _calls_on(stmt, f.line, {"execute", "executemany", "executescript"})
        if _fixed_first_arg(calls):
            return "the SQL text is written out in full; no outside value is built into it"
        if calls and all(c.args and _only_placeholders(c.args[0], src, f.line) for c in calls):
            return ("only '?' placeholders or quoted table and column names are built into the SQL text; "
                    "the values are passed separately")

    if f.rule_id in SHELL_RULES:
        calls = _calls_on(stmt, f.line, {"system", "popen", "run", "call", "check_call", "check_output", "Popen"})
        if _fixed_first_arg(calls):
            return "the command is written out in full; no outside value reaches the shell"

    if f.rule_id in SECRET_LIKE_RULES:
        if isinstance(stmt, (ast.If, ast.While, ast.Assert, ast.Return)) or any(
                isinstance(n, ast.Compare) and n.lineno <= f.line <= n.end_lineno for n in ast.walk(stmt)):
            compared = [_text(c) for n in ast.walk(stmt) if isinstance(n, ast.Compare)
                        for c in [n.left, *n.comparators] if _text(c) is not None]
            if compared and all(PLACEHOLDER.match(t) for t in compared):
                return "the code compares with an empty or placeholder value; no key is stored"
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            value = _text(stmt.value) if stmt.value is not None else None
            # Not "contains a space": `SECRET_KEY = 'my precious'` is a real key (fresh repos, 2026-10-27).
            if value is not None and value.lower() in TOKEN_TYPES:
                return "the value names a kind of token, it is not a key"

    if f.rule_id in ARCHIVE_RULES:
        calls = _calls_on(stmt, f.line, {"extractall", "extract"})
        zips = _zip_names(src.tree)
        if calls and all(isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name)
                         and c.func.value.id in zips for c in calls):
            return "a zip archive: Python's zipfile drops '..' and absolute names when extracting"

    if f.rule_id in URL_PREFIX_RULES:
        calls = _calls_on(stmt, f.line, {"startswith"})
        prefixes = [_text(a) for c in calls for a in c.args]
        prefixes += [_text(e) for c in calls for a in c.args if isinstance(a, ast.Tuple) for e in a.elts]
        prefixes = [p for p in prefixes if p is not None]
        if prefixes and not any("/" in p or ":" in p.rstrip(":") or p.lower().startswith("http") for p in prefixes):
            return "the prefixes are not web addresses"
    return None

