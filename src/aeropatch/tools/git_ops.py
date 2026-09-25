"""Scratch workspaces (doc 06 §9). A failed attempt never touches the source checkout.

Layout of a workspace directory:
    <tmp>/git/            git dir (kept out of the sandbox mount)
    <tmp>/src/repo/       working tree: scratch copy of the scenario repo
    <tmp>/src/changed.txt repo-relative paths touched by the current patch
Only <tmp>/src is mounted (read-only) into the sandbox.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Self

from aeropatch.tools.paths import safe_join

_GIT_ID = ["-c", "user.name=aeropatch", "-c", "user.email=aeropatch@localhost",
           "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false"]


class Workspace:
    def __init__(self, repo: Path):
        self.tmp = Path(tempfile.mkdtemp(prefix="aeropatch-"))
        self.src = self.tmp / "src"
        self.repo = self.src / "repo"
        shutil.copytree(repo, self.repo, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "pristine")
        (self.src / "changed.txt").write_text("")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()

    def _git(self, *args: str, input: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *_GIT_ID, f"--git-dir={self.tmp / 'git'}", f"--work-tree={self.repo}", *args],
            cwd=self.repo, input=input, capture_output=True, text=True, check=check,
            encoding="utf-8",
        )

    def read(self, rel: str) -> str:
        return safe_join(self.repo, rel).read_text(encoding="utf-8").replace("\r\n", "\n")

    def read_many(self, rels: list[str]) -> dict[str, str]:
        out = {}
        for rel in rels:
            p = safe_join(self.repo, rel)
            if p.is_file():
                out[rel] = self.read(rel)
        return out

    def write(self, changed: dict[str, str]) -> None:
        for rel, content in changed.items():
            p = safe_join(self.repo, rel)
            if not p.is_file():
                raise FileNotFoundError(rel)
            p.write_text(content, encoding="utf-8", newline="\n")
        self._record_changed()

    def apply_patch(self, patch: str) -> str:
        """git apply a patch; returns an error message, or '' on success."""
        if not patch.strip():
            return ""
        chk = self._git("apply", "--check", "-", input=patch, check=False)
        if chk.returncode != 0:
            return chk.stderr.strip()[:2000] or "git apply --check failed"
        self._git("apply", "-", input=patch)
        self._record_changed()
        return ""

    def diff(self) -> str:
        return self._git("diff", "--no-color").stdout

    def changed_paths(self) -> list[str]:
        out = self._git("diff", "--name-only").stdout
        return [line for line in out.splitlines() if line]

    def _record_changed(self) -> None:
        (self.src / "changed.txt").write_text("\n".join(self.changed_paths()) + "\n")

    def reset(self) -> None:
        """Back to the pristine commit: every attempt applies to the ORIGINAL code."""
        self._git("checkout", "-q", "--", ".")
        (self.src / "changed.txt").write_text("")

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
