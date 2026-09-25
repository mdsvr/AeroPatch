import subprocess
import sys

CODE = "from app.validate import is_valid_username; print(is_valid_username('a' * 40 + '!'))"


def test_long_invalid_name_is_rejected_quickly():
    # Run in a child process: a regex stuck in backtracking cannot be interrupted in-process.
    r = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, timeout=5)
    assert r.stdout.strip() == "False"
