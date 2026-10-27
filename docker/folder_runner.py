"""Start pytest on a user's folder (doc 17 part 4 §3). Copied into each folder image, never into the
base image, so the benchmark's runner is unchanged.

Plugin autoload stays on: the project's own plugins came with its dependencies. Each test's outcome
is written to /tmp/outcomes.txt as "<outcome>\\t<nodeid>". With AEROPATCH_PASS_SET pointing at a
file of node ids, only those tests run: the ones that passed both baseline runs.
"""

from __future__ import annotations

import os
import sys

import pytest

# The candidate code must win over the copy pip installed: the repo, and its src/ for a src layout.
ROOTS = [p for p in ("/work/repo/src", "/work/repo") if os.path.isdir(p)]
sys.path[:0] = ROOTS
os.environ["PYTHONPATH"] = os.pathsep.join(ROOTS)
PASS_SET = os.environ.get("AEROPATCH_PASS_SET", "")


class Outcomes:
    def __init__(self):
        self.out = open("/tmp/outcomes.txt", "w", encoding="utf-8")  # noqa: SIM115 - open for the whole run

    def pytest_collection_modifyitems(self, config, items):
        if PASS_SET and os.path.exists(PASS_SET):
            with open(PASS_SET, encoding="utf-8") as f:
                keep = {line.strip() for line in f if line.strip()}
            items[:] = [i for i in items if i.nodeid in keep]

    def pytest_runtest_logreport(self, report):
        # A test's outcome is its call phase, unless setup or teardown failed.
        if report.when == "call" or report.outcome == "failed":
            self.out.write(f"{report.outcome}\t{report.nodeid}\n")
            self.out.flush()


raise SystemExit(pytest.main(sys.argv[1:], plugins=[Outcomes()]))
