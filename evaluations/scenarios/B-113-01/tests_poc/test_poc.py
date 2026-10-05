import contextlib

import pytest

from microdot import Response

INJECTED = "\r\nSet-Cookie: role=admin"


def _header_values(response):
    values = []
    for value in response.headers.values():
        values += value if isinstance(value, list) else [value]
    return [str(value) for value in values]


@pytest.mark.parametrize("kwargs", [
    {"cookie": "session", "value": "abc" + INJECTED},
    {"cookie": "session", "value": "abc", "domain": "example.com" + INJECTED},
    {"cookie": "session", "value": "abc", "path": "/" + INJECTED},
    {"cookie": "session" + INJECTED + "; x", "value": "abc"},
    {"cookie": "session", "value": "abc", "expires": "Tue, 05 Nov 2019 02:23:54 GMT\nX-Injected: 1"},
])
def test_no_cookie_argument_can_add_a_header_line(kwargs):
    response = Response("ok")
    with contextlib.suppress(Exception):  # refusing the cookie is fine; emitting the line break is not
        response.set_cookie(**kwargs)
    assert not [value for value in _header_values(response) if "\r" in value or "\n" in value]
