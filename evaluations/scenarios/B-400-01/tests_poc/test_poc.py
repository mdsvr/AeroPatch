import subprocess
import sys

import pytest

from hpack.exceptions import HPACKDecodingError
from hpack.hpack import decode_integer

# RFC 7541, section 5.1: integer encodings that exceed implementation limits, in value or in
# octet length, MUST be treated as decoding errors.
CHILD = """
import sys
from hpack.exceptions import HPACKDecodingError
from hpack.hpack import decode_integer
try:
    decode_integer(bytes([255]) * 600_000 + bytes([0]), 8)
    print("decoded")
except HPACKDecodingError:
    print("error")
"""


@pytest.mark.parametrize("continuation_bytes", [64, 1_000])
def test_integer_with_far_too_many_continuation_bytes_is_a_decoding_error(continuation_bytes):
    with pytest.raises(HPACKDecodingError):
        decode_integer(bytes([0x1F]) + bytes([0xFF]) * continuation_bytes + bytes([0x01]), 5)


def test_huge_run_of_continuation_bytes_is_refused_quickly():
    # In a child process: the unbounded decode cannot be interrupted in-process.
    out = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, timeout=5).stdout.strip()
    assert out == "error"
