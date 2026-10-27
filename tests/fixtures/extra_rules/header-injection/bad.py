from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        lang = parse_qs(urlparse(self.path).query).get("lang", ["en"])[0]
        self.send_response(200)
        self.send_header("Content-Language", lang)
        self.end_headers()


def app(environ, start_response):
    name = environ.get("QUERY_STRING", "")
    start_response("200 OK", [("Content-Type", "text/plain"), ("X-Name", name)])
    return [b"ok"]
