"""Phase 1b exit criterion 2 (doc 17 part 4 §5): on 1a's public repos, how many build and collect
their tests in the folder sandbox, and why the others do not. One image at a time; each is
removed after its result is written, since each is about 1-1.5 GB.

    python evaluations/tools/folder_setup.py D:/aeropatch-repos --out docs/results/folder-setup.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeropatch import folder


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("repos", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    rows = []
    for repo in sorted(d for d in a.repos.iterdir() if d.is_dir()):
        start = time.monotonic()
        row = {"repo": repo.name}
        try:
            prep = folder.prepare(repo, rebuild=True)
            row.update(result="built and collected", tests_passing_twice=len(prep.pass_set), flaky=len(prep.flaky),
                       note=prep.note)
        except folder.FolderError as e:
            row.update(result=e.kind, message=str(e))
        except Exception as e:  # noqa: BLE001 - recorded, so one repo does not stop the rest
            row.update(result="HARNESS_ERROR", message=f"{type(e).__name__}: {e}"[:500])
        row["seconds"] = round(time.monotonic() - start)
        rows.append(row)
        print(json.dumps(row), flush=True)
        try:
            import docker

            docker.from_env().images.remove(folder.image_tag(repo), force=True)
        except Exception:  # noqa: BLE001, S110 - no image when the build failed
            pass
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    ok = sum(r["result"] == "built and collected" for r in rows)
    print(f"\n{ok} of {len(rows)} built and collected tests that pass twice")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
