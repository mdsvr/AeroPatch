from app.files import count_lines


def test_name_with_spaces_is_one_argument(tmp_path):
    (tmp_path / "my notes.txt").write_text("a\nb\nc\n")
    assert count_lines(tmp_path, "my notes.txt") == 3


def test_shell_metacharacters_are_literal(tmp_path):
    (tmp_path / "x;y.txt").write_text("a\nb\n")
    assert count_lines(tmp_path, "x;y.txt") == 2
