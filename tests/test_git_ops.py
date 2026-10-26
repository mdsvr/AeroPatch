"""Scratch workspaces keep a file's own line endings (doc 17; found on the user's CRLF repos 2026-10-24)."""

from aeropatch.tools.git_ops import Workspace


def test_a_crlf_file_stays_crlf_and_its_diff_shows_only_the_change(tmp_path):
    (tmp_path / "app.py").write_bytes(b"a = 1\r\nb = 2\r\nc = 3\r\n")
    (tmp_path / "unix.py").write_bytes(b"x = 1\n")
    with Workspace(tmp_path) as ws:
        ws.write({"app.py": ws.read("app.py").replace("b = 2", "b = 20"),
                  "unix.py": ws.read("unix.py").replace("1", "10")})
        assert (ws.repo / "app.py").read_bytes() == b"a = 1\r\nb = 20\r\nc = 3\r\n"
        assert (ws.repo / "unix.py").read_bytes() == b"x = 10\n"
        changed = [line for line in ws.diff().splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")]
        assert len(changed) == 4  # one line removed and one added per file, not the whole file
