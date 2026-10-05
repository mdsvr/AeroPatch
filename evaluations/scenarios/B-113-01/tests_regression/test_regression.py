"""Cookie and redirect tests from microdot's own tests/test_response.py."""
import pytest

from microdot import Response


def test_cookies():
    res = Response("ok")
    res.set_cookie("foo1", "bar1")
    res.set_cookie("foo2", "bar2", path="/", partitioned=True)
    res.set_cookie("foo3", "bar3", domain="example.com:1234")
    res.set_cookie("foo4", "bar4", expires="Tue, 05 Nov 2019 02:23:54 GMT")
    res.set_cookie("foo5", "bar5", max_age=123, expires="Thu, 01 Jan 1970 00:00:00 GMT")
    res.set_cookie("foo6", "bar6", secure=True, http_only=True)
    res.set_cookie("foo7", "bar7", path="/foo", domain="example.com:1234",
                   expires="Tue, 05 Nov 2019 02:23:54 GMT", max_age=123, secure=True, http_only=True)
    res.delete_cookie("foo8", http_only=True)
    res.delete_cookie("foo9", path="/s")
    assert res.headers == {"Set-Cookie": [
        "foo1=bar1",
        "foo2=bar2; Path=/; Partitioned",
        "foo3=bar3; Domain=example.com:1234",
        "foo4=bar4; Expires=Tue, 05 Nov 2019 02:23:54 GMT",
        "foo5=bar5; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=123",
        "foo6=bar6; Secure; HttpOnly",
        "foo7=bar7; Path=/foo; Domain=example.com:1234; Expires=Tue, 05 Nov 2019 02:23:54 GMT; Max-Age=123; "
        "Secure; HttpOnly",
        "foo8=; Expires=Thu, 01 Jan 1970 00:00:01 GMT; Max-Age=0; HttpOnly",
        "foo9=; Path=/s; Expires=Thu, 01 Jan 1970 00:00:01 GMT; Max-Age=0",
    ]}


def test_cookie_values_with_ordinary_punctuation_are_kept():
    res = Response("ok")
    res.set_cookie("prefs", "theme=dark&lang=en-GB; tz=+05:30")
    res.set_cookie("token", "a.b-c_d~e", path="/app/v1")
    assert res.headers["Set-Cookie"] == ["prefs=theme=dark&lang=en-GB; tz=+05:30", "token=a.b-c_d~e; Path=/app/v1"]


def test_set_cookie_keeps_other_headers():
    res = Response("ok", headers={"X-Request": "1"})
    res.set_cookie("a", "1")
    res.set_cookie("b", "2")
    assert res.headers["X-Request"] == "1" and res.headers["Set-Cookie"] == ["a=1", "b=2"]


def test_redirect():
    res = Response.redirect("/foo")
    assert res.status_code == 302 and res.headers["Location"] == "/foo"
    assert Response.redirect("/foo", status_code=301).status_code == 301
    with pytest.raises(ValueError):
        Response.redirect("/foo\x0d\x0a\x0d\x0a<p>Foo</p>")
