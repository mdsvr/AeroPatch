from http.server import BaseHTTPRequestHandler

MAX_BODY = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            self.send_error(413)
            return
        body = self.rfile.read(n)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body[:10])
