"""Scoped context for a finding (doc 06 §5), sized for a 4B model (target <= 3k tokens).

tree-sitter is error-tolerant, so this works on files that do not parse. Code is shown without
line-number prefixes (the model must copy SEARCH text verbatim); line ranges go in a header.
"""

from __future__ import annotations

import re
from pathlib import Path

import tree_sitter_python as tsp
from tree_sitter import Language, Node, Parser

from aeropatch.contracts import Context
from aeropatch.tools.paths import safe_join

PY = Language(tsp.language())
_parser = Parser(PY)

FUNC = ("function_definition",)
MAX_CALLERS = 2
SMALL_FILE_LINES = 60


def _parse(src: bytes):
    return _parser.parse(src)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _outer(node: Node) -> Node:
    """Include decorators: return the decorated_definition wrapper when present."""
    return node.parent if node.parent is not None and node.parent.type == "decorated_definition" else node


def _name(node: Node, src: bytes) -> str:
    n = node.child_by_field_name("name")
    return _text(n, src) if n else ""


def enclosing(tree, row: int) -> list[Node]:
    """Chain of function/class definitions containing `row` (0-based), outermost first."""
    chain = []
    node = tree.root_node
    while True:
        nxt = None
        for child in node.named_children:
            if child.start_point[0] <= row <= child.end_point[0]:
                nxt = child
                break
        if nxt is None:
            return chain
        if nxt.type in ("function_definition", "class_definition"):
            chain.append(nxt)
        node = nxt


def qualified_name(chain: list[Node], src: bytes) -> str:
    return ".".join(_name(n, src) for n in chain)


def _lines(src: bytes, start: int, end: int) -> str:
    return "\n".join(src.decode("utf-8", "replace").split("\n")[start:end + 1])


def _header(start: int, end: int) -> str:
    return f"# lines {start + 1}-{end + 1}"


def render_scope(src: bytes, row: int) -> tuple[str, str]:
    """Imports + referenced constants + enclosing function (or class header + method)."""
    tree = _parse(src)
    root = tree.root_node
    parts: list[str] = []
    imports = [c for c in root.named_children if c.type in ("import_statement", "import_from_statement")]
    if imports:
        parts.append(_header(imports[0].start_point[0], imports[-1].end_point[0]))
        parts.append("\n".join(_text(i, src) for i in imports))

    chain = enclosing(tree, row)
    funcs = [n for n in chain if n.type in FUNC]
    if not funcs:
        n_lines = src.count(b"\n") + 1
        lo, hi = (0, n_lines - 1) if n_lines <= SMALL_FILE_LINES else (max(0, row - 15), row + 15)
        parts.append(_header(lo, hi))
        parts.append(_lines(src, lo, hi))
        return "\n\n".join(parts), ""

    target = _outer(funcs[0])  # outermost function: nested helpers stay in view
    body = _text(target, src)
    consts = []
    for c in root.named_children:
        if c.type == "expression_statement" and c.named_children and c.named_children[0].type == "assignment":
            left = c.named_children[0].child_by_field_name("left")
            if left is not None and re.search(rf"\b{re.escape(_text(left, src))}\b", body):
                consts.append(c)
    for c in consts:
        parts.append(_header(c.start_point[0], c.end_point[0]))
        parts.append(_text(c, src))

    cls = next((n for n in chain if n.type == "class_definition" and n.start_point[0] < target.start_point[0]), None)
    if cls is not None:
        head_end = cls.child_by_field_name("body").start_point[0] - 1
        parts.append(_header(_outer(cls).start_point[0], head_end))
        parts.append(_lines(src, _outer(cls).start_point[0], head_end))
        sigs = []
        for m in cls.child_by_field_name("body").named_children:
            fn = m.child_by_field_name("definition") if m.type == "decorated_definition" else m
            if fn is not None and fn.type in FUNC and _outer(fn) != target:
                sigs.append("    " + _text(fn, src).split("\n", 1)[0] + " ...")
        if sigs:
            parts.append("# other methods (signatures only)\n" + "\n".join(sigs))

    start, end = target.start_point[0], target.end_point[0]
    indent = " " * target.start_point[1]
    parts.append(_header(start, end))
    parts.append(indent + body)
    return "\n\n".join(parts), qualified_name(chain, src)


def find_callers(repo: Path, name: str, skip: tuple[str, int] | None = None) -> list[str]:
    """Up to MAX_CALLERS call sites by name match (approximate; no type-resolved call graph)."""
    if not name:
        return []
    pat = re.compile(rf"(?<!def )\b{re.escape(name)}\s*\(")
    out = []
    for py in sorted(repo.rglob("*.py")):
        rel = py.relative_to(repo).as_posix()
        if "test" in rel.split("/")[-1]:
            continue
        lines = py.read_text(encoding="utf-8", errors="replace").split("\n")
        for i, line in enumerate(lines):
            if pat.search(line) and not line.lstrip().startswith("def "):
                if skip and rel == skip[0] and abs(i - skip[1]) < 1:
                    continue
                lo, hi = max(0, i - 3), min(len(lines) - 1, i + 3)
                out.append(f"# {rel} {_header(lo, hi)[2:]}\n" + "\n".join(lines[lo:hi + 1]))
                if len(out) >= MAX_CALLERS:
                    return out
    return out


def get_context(repo: Path, path: str, line: int, extra_paths: list[str] | None = None) -> Context:
    """Context for a finding at repo-relative `path`:`line` (1-based)."""
    repo = repo.resolve()
    file = safe_join(repo, path)
    src = file.read_bytes().replace(b"\r\n", b"\n")
    scope, target = render_scope(src, max(0, line - 1))
    files = {path: scope}
    func_name = target.rsplit(".", 1)[-1] if target else ""
    callers = find_callers(repo, func_name)
    if callers:
        files[path] += "\n\n# call sites (context only)\n" + "\n\n".join(callers)
    for extra in extra_paths or []:
        if extra == path:
            continue
        p = safe_join(repo, extra)
        if p.is_file():
            text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
            files[extra] = f"{_header(0, text.count(chr(10)))}\n{text}"
    tokens = sum(len(s) for s in files.values()) // 4
    return Context(files=files, token_count=tokens, target=target)


def function_span(src: str, qualified: str) -> tuple[int, int] | None:
    """1-based (start, end) lines of a function by qualified name, via tree-sitter."""
    data = src.encode()
    tree = _parse(data)

    def walk(node: Node, prefix: str):
        for child in node.named_children:
            inner = child.child_by_field_name("definition") if child.type == "decorated_definition" else child
            if inner is None:
                continue
            if inner.type in ("function_definition", "class_definition"):
                q = f"{prefix}.{_name(inner, data)}" if prefix else _name(inner, data)
                if q == qualified and inner.type in FUNC:
                    return inner.start_point[0] + 1, inner.end_point[0] + 1
                body = inner.child_by_field_name("body")
                if body is not None:
                    hit = walk(body, q)
                    if hit:
                        return hit
        return None

    return walk(tree.root_node, "")
