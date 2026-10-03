import contextlib
import json

from app.messages import decode


def _decode(message):
    with contextlib.suppress(Exception):  # refusing the message is fine; acting on it is not
        decode(json.dumps(message))


def test_decode_does_not_call_a_function_named_in_the_message(tmp_path):
    marker = tmp_path / "made-by-decode"
    _decode({"job": "resize", "target": {"__type__": "os.mkdir", "args": [str(marker)]}})
    assert not marker.exists()


def test_decode_cannot_delete_a_directory(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "invoice.pdf").write_bytes(b"%PDF-1.7")
    _decode({"__type__": "shutil.rmtree", "args": [str(uploads)]})
    assert (uploads / "invoice.pdf").exists()


def test_decode_does_not_run_code_from_the_message(tmp_path):
    marker = tmp_path / "made-by-exec"
    code = f"import pathlib; pathlib.Path({str(marker)!r}).write_text('x')"
    _decode({"job": "report", "steps": [{"__type__": "builtins.exec", "args": [code]}]})
    assert not marker.exists()
