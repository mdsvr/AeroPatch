import pytest

from mako import lookup

OUTSIDE_TEXT = "payroll figures for the board only"


@pytest.fixture
def site(tmp_path):
    templates = tmp_path / "app" / "templates"
    templates.mkdir(parents=True)
    (templates / "index.html").write_text("Hello")
    private = tmp_path / "private"
    private.mkdir()
    (private / "payroll.txt").write_text(OUTSIDE_TEXT)
    return lookup.TemplateLookup(directories=[str(templates)])


def _rendered(site, uri):
    try:
        return site.get_template(uri).render()
    except Exception:  # refusing the uri is the point
        return ""


@pytest.mark.parametrize("prefix", ["//", "///", "////"])
def test_extra_leading_slashes_do_not_reach_a_file_outside_the_template_root(site, prefix):
    assert OUTSIDE_TEXT not in _rendered(site, prefix + "../../private/payroll.txt")


def test_double_slash_with_a_longer_way_out_does_not_reach_the_file(site):
    assert OUTSIDE_TEXT not in _rendered(site, "//../templates/../../private/payroll.txt")
