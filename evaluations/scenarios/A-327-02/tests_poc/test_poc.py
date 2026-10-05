import struct

from app.signing import read_query, signed_query

SIGNING_KEY = b"k" * 24  # the forger never reads it; only its length is assumed
NOW = 1_700_000_000


def _cube_root_bits(prime):
    """First 32 bits of the fractional part of the cube root of `prime` (SHA-256 constant)."""
    target = prime << 96
    root = round(target ** (1 / 3))
    while root ** 3 > target:
        root -= 1
    while (root + 1) ** 3 <= target:
        root += 1
    return root & 0xFFFFFFFF


def _primes(count):
    found, candidate = [], 2
    while len(found) < count:
        if all(candidate % p for p in found):
            found.append(candidate)
        candidate += 1
    return found


ROUND_CONSTANTS = [_cube_root_bits(p) for p in _primes(64)]


def _rotr(value, bits):
    return ((value >> bits) | (value << (32 - bits))) & 0xFFFFFFFF


def _compress(state, block):
    w = list(struct.unpack(">16I", block))
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)
    a, b, c, d, e, f, g, h = state
    for i in range(64):
        t1 = (h + (_rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)) + ((e & f) ^ (~e & g))
              + ROUND_CONSTANTS[i] + w[i]) & 0xFFFFFFFF
        t2 = ((_rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) & 0xFFFFFFFF
        a, b, c, d, e, f, g, h = (t1 + t2) & 0xFFFFFFFF, a, b, c, (d + t1) & 0xFFFFFFFF, e, f, g
    return [(x + y) & 0xFFFFFFFF for x, y in zip(state, (a, b, c, d, e, f, g, h))]


def _padding(length):
    return b"\x80" + b"\x00" * ((55 - length) % 64) + struct.pack(">Q", length * 8)


def _extend(query, extra, key_length):
    """Forge a longer signed query from a genuine one, without the key.

    A plain hash of key + text can be continued from its own output: the signature is the
    hash state after the genuine text, so hashing `extra` from that state gives the signature
    of the genuine text, its padding and `extra`.
    """
    signed, _, signature = query.rpartition(b"&sig=")
    try:
        state = list(struct.unpack(">8I", bytes.fromhex(signature.decode("ascii"))))
    except (ValueError, struct.error):
        return None  # not a 256-bit hex signature: this forgery does not apply
    glue = _padding(key_length + len(signed))
    tail = extra + _padding(key_length + len(signed) + len(glue) + len(extra))
    for start in range(0, len(tail), 64):
        state = _compress(state, tail[start:start + 64])
    return signed + glue + extra + b"&sig=" + struct.pack(">8I", *state).hex().encode("ascii")


def _fields(query):
    if query is None:
        return {}
    try:
        return read_query(SIGNING_KEY, query)
    except Exception:  # refusing the query string is the point
        return {}


def test_extended_query_does_not_change_the_file():
    genuine = signed_query(SIGNING_KEY, {"file": "manual.pdf", "expires": str(NOW + 60)})
    forged = _extend(genuine, b"&file=payroll-2026.xlsx", len(SIGNING_KEY))
    assert _fields(genuine).get("file") == "manual.pdf"
    assert _fields(forged).get("file") != "payroll-2026.xlsx"


def test_extended_query_does_not_move_the_expiry():
    genuine = signed_query(SIGNING_KEY, {"file": "manual.pdf", "expires": str(NOW - 3600)})
    forged = _extend(genuine, b"&expires=" + str(NOW + 10 ** 6).encode("ascii"), len(SIGNING_KEY))
    assert _fields(forged) == {}
