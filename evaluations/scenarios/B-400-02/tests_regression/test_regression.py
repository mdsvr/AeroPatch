"""Real value tests from pyasn1's own tests/type/test_univ.py (RealTestCase), plus a BER round trip."""
import pytest

from pyasn1.codec.ber import decoder, encoder
from pyasn1.type import univ


def test_float_and_int():
    assert float(univ.Real(4.0)) == 4.0
    assert int(univ.Real(3.0)) == 3
    assert univ.Real((0.25, 2, 3)) == 2.0
    assert univ.Real((3, 10, 0)) == 3


def test_float_keeps_base_10_and_base_2_values():
    assert float(univ.Real((3, 10, 23))) == 3e23
    assert float(univ.Real((123, 10, -2))) == 1.23
    assert float(univ.Real((5, 2, 3))) == 40.0
    assert float(univ.Real((-7, 2, -1))) == -3.5
    assert float(univ.Real((1, 10, -400))) == 0.0
    assert float(univ.Real((1, 2, -1000000))) == 0.0


def test_float_too_large_raises_overflow_error():
    with pytest.raises(OverflowError):
        float(univ.Real((1, 2, 1000000)))
    with pytest.raises(OverflowError):
        float(univ.Real((1, 10, 400)))


def test_arithmetic():
    assert univ.Real(-4.1) + 1.4 == -2.7
    assert 4 + univ.Real(0.5) == 4.5
    assert univ.Real(3.0) * -3 == -9
    assert univ.Real(3.0) / 2 == 1.5
    assert univ.Real(3.0) % 2 == 1
    assert univ.Real(3.0) ** 2 == 9
    assert abs(univ.Real(-2.5)) == 2.5


def test_str_and_pretty_print():
    assert str(univ.Real(1.0)) == "1.0"
    assert univ.Real((123, 10, 11)).prettyPrint() == "12300000000000.0"
    assert "Real" in repr(univ.Real(-4.1))


def test_infinities():
    assert str(univ.Real("inf")) == "inf"
    assert univ.Real("inf") + 1 == float("inf")
    assert float(univ.Real("-inf")) == float("-inf")
    assert univ.Real("inf").isPlusInf and univ.Real("-inf").isMinusInf
    with pytest.raises(OverflowError):
        int(univ.Real("inf"))


def test_ber_round_trip_of_ordinary_reals():
    for value in (univ.Real((123, 10, 11)), univ.Real((1, 2, 3)), univ.Real(-0.5), univ.Real("inf")):
        decoded, rest = decoder.decode(encoder.encode(value), asn1Spec=univ.Real())
        assert not rest and decoded == value and float(decoded) == float(value)
