"""Start pytest before adding the candidate repository to the import path."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "/work/repo")
# Tests that spawn a child interpreter (e.g. the ReDoS PoC) must be able to import the repo too.
os.environ["PYTHONPATH"] = "/work/repo"
raise SystemExit(pytest.main(sys.argv[1:]))
