"""Integer and header-block decoding, following hpack's own tests/test_encode_decode.py and
tests/test_hpack.py (the RFC 7541 appendix C examples)."""
import pytest

from hpack import Decoder, Encoder
from hpack.exceptions import HPACKDecodingError
from hpack.hpack import decode_integer, encode_integer


@pytest.mark.parametrize("data, prefix_bits, expected", [
    (b"\x0a", 5, (10, 1)),              # RFC 7541 C.1.1
    (b"\x1f\x9a\x0a", 5, (1337, 3)),    # RFC 7541 C.1.2
    (b"\x2a", 8, (42, 1)),              # RFC 7541 C.1.3
    (b"\x1f\x00", 5, (31, 2)),
    (b"\xff\x00trailing", 8, (255, 2)),
])
def test_decode_integer_examples(data, prefix_bits, expected):
    assert decode_integer(data, prefix_bits) == expected


@pytest.mark.parametrize("prefix_bits", range(1, 9))
def test_encode_decode_round_trips_up_to_32_bits(prefix_bits):
    for integer in (0, 1, 30, 31, 127, 128, 255, 256, 16_383, 65_535, 2 ** 24 + 7, 2 ** 31 - 1, 2 ** 32 - 1, 2 ** 32):
        encoded = bytes(encode_integer(integer, prefix_bits))
        assert decode_integer(encoded, prefix_bits) == (integer, len(encoded))


def test_truncated_integer_is_a_decoding_error():
    for data in (b"", b"\x1f", b"\x1f\x9a", b"\x1f\xff\xff"):
        with pytest.raises(HPACKDecodingError):
            decode_integer(data, 5)


def test_prefix_bits_out_of_range():
    for prefix_bits in (0, 9, -1):
        with pytest.raises(ValueError):
            decode_integer(b"\x0a", prefix_bits)


def test_header_block_round_trips():
    headers = [(":method", "GET"), (":path", "/search?q=" + "x" * 300), ("x-request-id", "42"),
               ("cookie", "a=1; b=2"), ("accept", "*/*")]
    encoder, decoder = Encoder(), Decoder()
    assert decoder.decode(encoder.encode(headers)) == headers
    assert decoder.decode(encoder.encode(headers)) == headers  # second block uses the dynamic table


def test_rfc_request_example_without_huffman():
    # RFC 7541 C.3.1
    data = bytes.fromhex("828684410f7777772e6578616d706c652e636f6d")
    assert Decoder().decode(data) == [(":method", "GET"), (":scheme", "http"), (":path", "/"),
                                      (":authority", "www.example.com")]
