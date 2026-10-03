import contextlib

import pytest

from app.logviewer import count_matches

LOG = "start worker\ndisk full on /var\ncan't open socket\ndisk full on /tmp\nstop worker\n"


@pytest.fixture
def logs(tmp_path):
    (tmp_path / "app.log").write_text(LOG)
    return tmp_path


def _search(logs, term):
    with contextlib.suppress(Exception):  # failing on the odd term is fine; running it is not
        return count_matches(str(logs), "app.log", term)
    return None


def test_command_after_a_semicolon_is_not_run(logs):
    marker = logs / "made-by-search"
    _search(logs, f"worker; touch {marker} ")
    assert not marker.exists()


def test_command_substitution_is_not_run(logs):
    marker = logs / "made-by-substitution"
    _search(logs, f"$(touch {marker})worker")
    assert not marker.exists()


def test_term_with_a_space_is_one_search_text(logs):
    assert count_matches(str(logs), "app.log", "disk full") == 2


def test_term_with_a_quote_is_plain_text(logs):
    assert count_matches(str(logs), "app.log", "can't") == 1
