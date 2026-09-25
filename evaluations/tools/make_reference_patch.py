"""Write a scenario's reference_fix.patch from a fixed copy of one or more repo files.

    uv run python evaluations/tools/make_reference_patch.py A-089-01 app/db.py=/path/to/fixed_db.py
"""

import shutil
import sys

from aeropatch.scenario import scenario_dir
from aeropatch.tools.git_ops import Workspace


def main() -> None:
    sid, *pairs = sys.argv[1:]
    d = scenario_dir(sid)
    with Workspace(d / "repo") as ws:
        for pair in pairs:
            rel, fixed = pair.split("=", 1)
            shutil.copyfile(fixed, ws.repo / rel)
        (d / "reference_fix.patch").write_text(ws.diff(), encoding="utf-8")
    print((d / "reference_fix.patch").read_text())


if __name__ == "__main__":
    main()
