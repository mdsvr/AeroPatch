"""Harness self-check route: converts a scenario's reference fix into SEARCH/REPLACE blocks.

It never reaches a model. If the `oracle` config does not resolve every scenario, the bug is in
the harness (edit engine, gates, sandbox) or the scenario, not in a model.
"""

from __future__ import annotations

from pathlib import Path

from aeropatch.models.base import Generation


def patch_to_blocks(patch: str) -> str:
    blocks: list[str] = []
    path = ""
    search: list[str] = []
    replace: list[str] = []

    def flush() -> None:
        if search or replace:
            blocks.append(f"<<<<<<< SEARCH {path}\n" + "\n".join(search) + "\n=======\n"
                          + "\n".join(replace) + "\n>>>>>>> REPLACE")

    for line in patch.splitlines():
        if line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
        elif line.startswith("@@"):
            flush()
            search, replace = [], []
        elif line.startswith(("--- ", "diff ", "index ")):
            continue
        elif line.startswith("-"):
            search.append(line[1:])
        elif line.startswith("+"):
            replace.append(line[1:])
        elif line.startswith(" ") or line == "":
            search.append(line[1:])
            replace.append(line[1:])
    flush()
    return "RATIONALE: reference fix\n" + "\n".join(blocks)


def generate(scenario_dir: Path) -> Generation:
    patch = (scenario_dir / "reference_fix.patch").read_text(encoding="utf-8")
    return Generation(text=patch_to_blocks(patch), model="oracle")
