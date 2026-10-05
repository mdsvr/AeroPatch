import subprocess
import sys

# In a child process: building a number with a hundred million digits cannot be interrupted
# in-process. A decoded REAL carries its exponent as given by the sender.
CHILD = """
import sys
from pyasn1.type import univ
real = univ.Real((int(sys.argv[1]), 10, 100_000_000))
try:
    print(repr(float(real)) if sys.argv[2] == "float" else real.prettyPrint())
except OverflowError:
    print("OverflowError")
"""


def _run(mantissa, what):
    return subprocess.run([sys.executable, "-c", CHILD, str(mantissa), what], capture_output=True, text=True,
                          timeout=5).stdout.strip()


def test_float_of_a_real_with_a_huge_exponent_fails_fast():
    assert _run(1, "float") == "OverflowError"


def test_float_of_zero_with_a_huge_exponent_is_zero_at_once():
    assert _run(0, "float") == "0.0"


def test_pretty_print_of_a_real_with_a_huge_exponent_returns_at_once():
    assert _run(7, "pretty") != ""
