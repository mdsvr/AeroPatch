import subprocess
import sys

# Run in a child process: a regex stuck in backtracking cannot be interrupted in-process.
NAME = "from app.signup import is_valid_full_name; print(is_valid_full_name('a' * 40 + '1'))"
FORM = (
    "from app.signup import validate_signup; "
    "form = {'username': 'ada_l', 'full_name': 'x' * 45 + '!', 'postcode': 'SW1A 1AA', 'phone': '+442079460000'}; "
    "print(sorted(validate_signup(form)))"
)


def _run(code):
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5).stdout.strip()


def test_long_invalid_name_is_rejected_quickly():
    assert _run(NAME) == "False"


def test_form_with_long_invalid_name_is_answered_quickly():
    assert _run(FORM) == "['full_name']"
