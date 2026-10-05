import subprocess
import sys

# Run in a child process: a regex stuck in backtracking cannot be interrupted in-process.
TEMPLATE = """
from geopy.point import Point
try:
    Point({payload})
    print("parsed")
except ValueError:
    print("ValueError")
"""


def _run(payload):
    code = TEMPLATE.format(payload=payload)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5).stdout.strip()


def test_long_run_of_spaces_is_rejected_quickly():
    assert _run("'<' + ' ' * 100_000 + 'X'") == "ValueError"


def test_coordinates_followed_by_a_long_run_of_spaces_are_answered_quickly():
    assert _run("'41.5 -81.0' + ' ' * 3_000 + 'X'") == "ValueError"
