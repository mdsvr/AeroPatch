import contextlib

from app.logtools import usage_kb


def test_name_with_spaces_is_one_argument(tmp_path):
    (tmp_path / "billing service.log").write_bytes(b"x" * 300_000)
    assert usage_kb(tmp_path, "billing service.log") >= 200


def test_shell_metacharacters_are_literal(tmp_path):
    (tmp_path / "a;b.log").write_bytes(b"x" * 300_000)
    assert usage_kb(tmp_path, "a;b.log") >= 200


def test_command_in_name_is_not_run(tmp_path):
    (tmp_path / "x.log").write_text("one line\n")
    with contextlib.suppress(Exception):  # failing on the odd name is fine; running it is not
        usage_kb(tmp_path, "x.log; touch pwned")
    assert not (tmp_path / "pwned").exists()
