import contextlib
import os
import pickle

from app.jobs import load_job, pending


class _Payload:
    """Unpickling this creates the marker directory."""

    def __init__(self, marker):
        self.marker = marker

    def __reduce__(self):
        return (os.mkdir, (self.marker,))


def _drop(spool, marker):
    spool.mkdir(exist_ok=True)
    path = spool / "0001.job"
    path.write_bytes(pickle.dumps(_Payload(str(marker))))
    return str(path)


def test_loading_a_pickled_job_runs_nothing(tmp_path):
    marker = tmp_path / "pwned"
    path = _drop(tmp_path / "spool", marker)
    with contextlib.suppress(Exception):  # rejecting the file is fine; running its payload is not
        load_job(path)
    assert not marker.exists()


def test_listing_pending_jobs_runs_nothing(tmp_path):
    marker = tmp_path / "pwned"
    _drop(tmp_path / "spool", marker)
    with contextlib.suppress(Exception):
        pending(str(tmp_path / "spool"))
    assert not marker.exists()
