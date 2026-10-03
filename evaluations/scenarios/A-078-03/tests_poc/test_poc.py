import contextlib
import tarfile

from app.bundles import create_bundle


def _workdir(tmp_path):
    (tmp_path / "sales.csv").write_text("region,total\nnorth,10\n")
    (tmp_path / "q3 summary.txt").write_text("all good\n")
    return str(tmp_path)


def test_command_in_label_is_not_run(tmp_path):
    workdir = _workdir(tmp_path)
    with contextlib.suppress(Exception):  # refusing the odd label is fine; running it is not
        create_bundle(workdir, "q3; touch pwned #", ["sales.csv"])
    assert not (tmp_path / "pwned").exists()


def test_command_substitution_in_label_is_not_run(tmp_path):
    workdir = _workdir(tmp_path)
    with contextlib.suppress(Exception):
        create_bundle(workdir, "q3-$(touch pwned)", ["sales.csv"])
    assert not (tmp_path / "pwned").exists()


def test_report_name_with_space_is_one_file(tmp_path):
    workdir = _workdir(tmp_path)
    path = create_bundle(workdir, "summary", ["q3 summary.txt"])
    with tarfile.open(path) as tar:
        assert tar.getnames() == ["q3 summary.txt"]
