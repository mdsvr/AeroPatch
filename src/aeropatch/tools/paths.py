"""Path validation shared by the edit engine and (later) the MCP boundary (doc 06 §4)."""

from __future__ import annotations

from pathlib import Path


class PathError(ValueError):
    pass


def safe_join(root: Path, rel: str) -> Path:
    """Resolve `rel` inside `root`; reject absolute paths, traversal and symlink escapes."""
    if not rel or rel.startswith(("/", "\\")) or (len(rel) > 1 and rel[1] == ":"):
        raise PathError(f"path must be repo-relative: {rel!r}")
    root = root.resolve()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathError(f"path escapes the repository: {rel!r}")
    # Reject symlinks anywhere along the way, even ones that point back inside.
    probe = root
    for part in Path(rel).parts:
        probe = probe / part
        if probe.is_symlink():
            raise PathError(f"symlinks are not allowed: {rel!r}")
    return candidate


def check_under_roots(path: Path, roots: list[Path]) -> Path:
    resolved = path.resolve()
    for root in roots:
        root = root.resolve()
        if resolved == root or root in resolved.parents:
            return resolved
    raise PathError(f"{path} is not under an allowlisted root")
