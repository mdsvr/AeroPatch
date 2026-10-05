"""TemplateLookup behaviour, following Mako's own test/test_lookup.py."""
import pytest

from mako import exceptions, lookup
from mako.template import Template


@pytest.fixture
def site(tmp_path):
    templates = tmp_path / "app" / "templates"
    (templates / "subdir").mkdir(parents=True)
    (templates / "index.html").write_text("Hello ${name}")
    (templates / "subdir" / "page.html").write_text('<%include file="/index.html" args="name=\'x\'"/> / page')
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "payroll.txt").write_text("outside")
    return lookup.TemplateLookup(directories=[str(templates)])


def test_templates_inside_the_root_render(site):
    assert site.get_template("index.html").render(name="world") == "Hello world"
    assert site.get_template("/index.html").render(name="world") == "Hello world"
    assert site.get_template("/subdir/page.html").uri == "/subdir/page.html"


def test_uri_whose_parent_steps_cancel_out_is_accepted(site):
    assert site.get_template("subdir/../index.html").render(name="a") == "Hello a"
    assert site.get_template("/subdir/../index.html").render(name="a") == "Hello a"


def test_extra_leading_slashes_inside_the_root_still_work(site):
    assert site.get_template("//index.html").render(name="b") == "Hello b"
    assert site.get_template("///subdir/page.html").uri == "///subdir/page.html"


def test_single_slash_uri_outside_the_root_is_refused(site):
    for uri in ("/../../private/payroll.txt", "../../private/payroll.txt"):
        with pytest.raises(exceptions.TemplateLookupException):
            site.get_template(uri)


def test_missing_template_raises_top_level_lookup(site):
    with pytest.raises(exceptions.TopLevelLookupException):
        site.get_template("nothing.html")


def test_template_object_keeps_its_uri_and_renders():
    template = Template("total: ${1 + 2}", uri="/reports/total.txt")
    assert template.uri == "/reports/total.txt" and template.render() == "total: 3"
    assert Template("plain").render() == "plain"
    with pytest.raises(exceptions.TemplateLookupException):
        Template("x", uri="../outside.txt")
