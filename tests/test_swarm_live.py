"""The swarm dashboard server refuses requests whose Host is not this computer (DNS rebinding)."""

import http.client
import importlib.util
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "swarm_live", Path(__file__).resolve().parents[1] / ".opencode" / "swarm_live.py")
swarm_live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(swarm_live)


def test_host_check():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), swarm_live.Handler)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        def status(host):
            con = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            con.request("GET", "/swarm.html", headers={"Host": host})
            code = con.getresponse().status
            con.close()
            return code
        assert status(f"127.0.0.1:{port}") == 200
        assert status(f"localhost:{port}") == 200
        assert status(f"evil.example:{port}") == 403
        assert status("127.0.0.1") == 403
    finally:
        srv.shutdown()
        srv.server_close()
