import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.messages import MessageError, decode, encode


def test_typed_values_round_trip():
    message = {"job": "invoice", "total": Decimal("19.90"), "due": date(2026, 10, 3),
               "retry_after": timedelta(days=2, seconds=30)}
    assert decode(encode(message)) == message
    assert isinstance(decode(encode(message))["total"], Decimal)


def test_plain_json_is_unchanged():
    message = {"job": "resize", "sizes": [64, 128], "options": {"crop": True, "note": None}}
    assert decode(encode(message)) == message
    assert decode('{"job": "ping"}') == {"job": "ping"}


def test_typed_values_inside_lists_and_objects():
    message = {"lines": [{"price": Decimal("4.50"), "ships": date(2026, 1, 31)}],
               "windows": [timedelta(seconds=90), timedelta(days=1)]}
    assert decode(encode(message)) == message


def test_wire_format_of_typed_values():
    assert json.loads(encode({"total": Decimal("1.5")})) == {
        "total": {"__type__": "decimal.Decimal", "args": ["1.5"]}}
    assert decode('{"due": {"__type__": "datetime.date", "args": [2026, 12, 24]}}') == {
        "due": date(2026, 12, 24)}
    assert decode('{"ttl": {"__type__": "datetime.timedelta", "args": [0, 45]}}') == {
        "ttl": timedelta(seconds=45)}


def test_bad_messages_raise():
    for text in ("not json", "[1, 2]", '"text"', "{"):
        with pytest.raises(MessageError):
            decode(text)
    with pytest.raises(MessageError):
        encode({"tags": {"a", "b"}})
    with pytest.raises(MessageError):
        encode(["not", "a", "dict"])
