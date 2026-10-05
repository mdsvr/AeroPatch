"""Wire format of the job queue: JSON, with a few typed values marked by "__type__"."""

import importlib
import json
from datetime import date, timedelta
from decimal import Decimal

TYPE_KEY = "__type__"


class MessageError(ValueError):
    """Raised for a message that cannot be encoded or decoded."""


def _mark(value):
    """json.dumps `default`: describe a typed value so that decode() can rebuild it."""
    if isinstance(value, Decimal):
        return {TYPE_KEY: "decimal.Decimal", "args": [str(value)]}
    if isinstance(value, date):
        return {TYPE_KEY: "datetime.date", "args": [value.year, value.month, value.day]}
    if isinstance(value, timedelta):
        return {TYPE_KEY: "datetime.timedelta", "args": [value.days, value.seconds]}
    raise MessageError(f"cannot encode {type(value).__name__}")


def _revive(obj):
    """json.loads `object_hook`: rebuild a value that _mark described."""
    if TYPE_KEY not in obj:
        return obj
    module_name, _, name = obj[TYPE_KEY].rpartition(".")
    factory = getattr(importlib.import_module(module_name), name)
    return factory(*obj.get("args", []))


def encode(message):
    """Serialize a message (a dict) for the queue."""
    if not isinstance(message, dict):
        raise MessageError("a message must be a dict")
    return json.dumps(message, default=_mark, sort_keys=True)


def decode(text):
    """Parse a message taken off the queue.

    Workers call this on everything they receive; any service on the network can enqueue.
    """
    try:
        message = json.loads(text, object_hook=_revive)
    except json.JSONDecodeError as exc:
        raise MessageError("message is not valid JSON") from exc
    if not isinstance(message, dict):
        raise MessageError("a message must be a JSON object")
    return message
