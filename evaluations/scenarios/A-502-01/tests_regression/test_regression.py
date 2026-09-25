import pytest

from app.prefs import DEFAULTS, dump_prefs, load_prefs


def test_round_trip():
    assert load_prefs(dump_prefs({"theme": "dark"})) == {"theme": "dark", "page_size": 20}


def test_round_trip_nested_values():
    prefs = {"page_size": 50, "columns": ["name", "size"], "flags": {"beta": True}}
    assert load_prefs(dump_prefs(prefs)) == {**DEFAULTS, **prefs}


def test_non_object_rejected():
    with pytest.raises(ValueError):
        load_prefs(dump_prefs([1, 2]))


def test_dump_returns_bytes():
    assert isinstance(dump_prefs({"a": 1}), bytes)
