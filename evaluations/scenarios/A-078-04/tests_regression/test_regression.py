import pytest

from app.logviewer import LogError, count_matches, last_lines, size_bytes

LOG = "".join(f"{i:02d} {'ERROR timeout' if i % 4 == 0 else 'INFO ok'} a.c\n" for i in range(1, 21))


@pytest.fixture
def logs(tmp_path):
    (tmp_path / "app.log").write_text(LOG)
    (tmp_path / "worker.log").write_text("abc\n")
    return str(tmp_path)


def test_count_matches_counts_lines(logs):
    assert count_matches(logs, "app.log", "ERROR") == 5
    assert count_matches(logs, "app.log", "INFO") == 15
    assert count_matches(logs, "app.log", "timeout") == 5


def test_no_match_is_zero(logs):
    assert count_matches(logs, "app.log", "FATAL") == 0


def test_term_is_plain_text_not_a_pattern(logs):
    assert count_matches(logs, "worker.log", "a.c") == 0
    assert count_matches(logs, "app.log", "a.c") == 20
    assert count_matches(logs, "app.log", "-c") == 0


def test_last_lines(logs):
    assert last_lines(logs, "app.log", 2) == ["19 INFO ok a.c", "20 ERROR timeout a.c"]
    assert len(last_lines(logs, "app.log")) == 10
    assert last_lines(logs, "worker.log", "5") == ["abc"]


def test_size_bytes(logs):
    assert size_bytes(logs, "worker.log") == 4
    assert size_bytes(logs, "app.log") == len(LOG)


def test_unknown_or_missing_log_raises(logs):
    with pytest.raises(LogError):
        count_matches(logs, "secrets.log", "x")
    with pytest.raises(LogError):
        last_lines(logs, "../app.log")
    with pytest.raises(LogError):
        count_matches(logs, "audit.log", "x")
    with pytest.raises(LogError):
        last_lines(logs, "audit.log")
    with pytest.raises(LogError):
        size_bytes(logs, "audit.log")
