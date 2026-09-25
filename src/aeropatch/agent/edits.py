"""Search/replace edit format: parsing and applying (doc 08 part 1, §5-6).

The model never writes a diff. It emits RATIONALE + SEARCH/REPLACE blocks; the harness applies
them to a scratch copy and `git diff` produces the patch.
"""

from __future__ import annotations

import difflib
import re
import textwrap
from dataclasses import dataclass

from aeropatch.contracts import Edit, EditProposal

SEARCH_RE = re.compile(r"^\s*<{5,9} SEARCH\s+(?P<path>\S+)\s*$")
DIVIDER_RE = re.compile(r"^\s*={5,9}\s*$")
REPLACE_RE = re.compile(r"^\s*>{5,9} REPLACE\s*$")
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

FORMAT_EXAMPLE = """\
RATIONALE: Use a parameterized query instead of string formatting.
<<<<<<< SEARCH app/db.py
    cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
=======
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
>>>>>>> REPLACE"""


class ApplyError(Exception):
    """An edit could not be applied. `code` is SEARCH_NOT_FOUND, SEARCH_AMBIGUOUS, etc."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def parse(text: str) -> EditProposal:
    """Parse model output. Text after the last REPLACE marker is ignored."""
    text = THINK_RE.sub("", text.replace("\r\n", "\n"))
    rationale = ""
    edits: list[Edit] = []
    state, path, search, replace = "out", "", [], []
    for line in text.split("\n"):
        if state == "out":
            m = SEARCH_RE.match(line)
            if m:
                state, path, search, replace = "search", m["path"].strip("`"), [], []
            elif not rationale and line.strip().upper().startswith("RATIONALE:"):
                rationale = line.split(":", 1)[1].strip()
        elif state == "search":
            if DIVIDER_RE.match(line):
                state = "replace"
            else:
                search.append(line)
        elif state == "replace":
            if REPLACE_RE.match(line):
                edits.append(Edit(path=path, search="\n".join(search), replace="\n".join(replace)))
                state = "out"
            else:
                replace.append(line)
    error = ""
    if state != "out":
        error = "FORMAT_ERROR: unterminated SEARCH/REPLACE block"
    elif not edits:
        error = "FORMAT_ERROR: no SEARCH/REPLACE blocks found"
    return EditProposal(edits=edits, rationale=rationale[:600], parse_error=error)


@dataclass
class _Window:
    start: int
    indent: str


def _common_indent(lines: list[str]) -> str:
    indents = [line[: len(line) - len(line.lstrip())] for line in lines if line.strip()]
    if not indents:
        return ""
    prefix = indents[0]
    for ind in indents[1:]:
        while not ind.startswith(prefix):
            prefix = prefix[:-1]
    return prefix


def _dedent(lines: list[str]) -> list[str]:
    return textwrap.dedent("\n".join(line.rstrip() for line in lines)).split("\n")


def _fuzzy_windows(file_lines: list[str], search_lines: list[str]) -> list[_Window]:
    target = _dedent(search_lines)
    n = len(search_lines)
    hits = []
    for i in range(len(file_lines) - n + 1):
        window = file_lines[i : i + n]
        if _dedent(window) == target:
            hits.append(_Window(i, _common_indent(window)))
    return hits


def _closest(file_lines: list[str], search_lines: list[str]) -> str:
    probe = next((s for s in search_lines if s.strip()), "")
    stripped = [line.strip() for line in file_lines]
    matches = difflib.get_close_matches(probe.strip(), stripped, n=2, cutoff=0.5)
    out = []
    for m in matches:
        i = stripped.index(m)
        out.append("\n".join(file_lines[max(0, i - 2) : i + 3]))
    return "\n...\n".join(out)


def _trim_blank_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def apply_one(content: str, edit: Edit) -> str:
    search_lines = _trim_blank_edges(edit.search.split("\n"))
    if not search_lines:
        raise ApplyError("EMPTY_SEARCH", f"{edit.path}: SEARCH must quote existing lines")
    search = "\n".join(search_lines)
    replace_lines = _trim_blank_edges(edit.replace.split("\n"))

    # 1. Exact match of whole lines.
    file_lines = content.split("\n")
    exact = [
        i for i in range(len(file_lines) - len(search_lines) + 1)
        if file_lines[i : i + len(search_lines)] == search_lines
    ]
    if len(exact) == 1:
        i = exact[0]
        return "\n".join(file_lines[:i] + replace_lines + file_lines[i + len(search_lines) :])
    if len(exact) > 1:
        raise ApplyError(
            "SEARCH_AMBIGUOUS",
            f"{edit.path}: SEARCH text matches {len(exact)} places; include more surrounding lines",
        )

    # 2. Whitespace-tolerant match: trailing spaces and a uniform indent shift are ignored.
    windows = _fuzzy_windows(file_lines, search_lines)
    if len(windows) == 1:
        w = windows[0]
        new = [w.indent + line if line.strip() else "" for line in _dedent(replace_lines)]
        if not replace_lines:
            new = []
        return "\n".join(file_lines[: w.start] + new + file_lines[w.start + len(search_lines) :])
    if len(windows) > 1:
        raise ApplyError(
            "SEARCH_AMBIGUOUS",
            f"{edit.path}: SEARCH text matches {len(windows)} places; include more surrounding lines",
        )

    closest = _closest(file_lines, search_lines)
    hint = f"\nClosest lines in the file:\n{closest}" if closest else ""
    raise ApplyError("SEARCH_NOT_FOUND", f"{edit.path}: SEARCH text not found:\n{search}{hint}")


def apply_edits(files: dict[str, str], edits: list[Edit]) -> dict[str, str]:
    """Apply edits in order to in-memory file contents. Returns the changed files only."""
    current = dict(files)
    changed: dict[str, str] = {}
    for edit in edits:
        if edit.path not in current:
            raise ApplyError("UNKNOWN_FILE", f"{edit.path}: file does not exist (new files are not allowed)")
        current[edit.path] = apply_one(current[edit.path], edit)
        changed[edit.path] = current[edit.path]
    return changed


def normalized_hash(edits: list[Edit]) -> str:
    """Stable hash of an edit set, for identical-edit detection on repair attempts."""
    import hashlib

    h = hashlib.sha256()
    for e in edits:
        for part in (e.path, "\n".join(_dedent(e.search.split("\n"))), "\n".join(_dedent(e.replace.split("\n")))):
            h.update(part.strip().encode())
            h.update(b"\0")
    return h.hexdigest()[:16]
