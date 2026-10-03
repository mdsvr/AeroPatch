import contextlib

from app.sitemap import read_sitemap

MARKER = "INTERNAL-ONLY-HOST-LIST"


def _read(document):
    with contextlib.suppress(Exception):  # refusing the sitemap is fine; reading local files is not
        return read_sitemap(document.encode())
    return []


def test_external_entity_is_not_read_into_the_entries(tmp_path):
    private_file = tmp_path / "hosts.txt"
    private_file.write_text(MARKER)
    document = (
        f'<?xml version="1.0"?><!DOCTYPE urlset [<!ENTITY ext SYSTEM "{private_file.as_uri()}">]>'
        "<urlset><url><loc>https://a.example/&ext;</loc></url></urlset>"
    )
    assert MARKER not in str(_read(document))


def test_external_dtd_is_not_loaded(tmp_path):
    dtd = tmp_path / "shared.dtd"
    dtd.write_text(f'<!ENTITY inc "{MARKER}">')
    document = (
        f'<?xml version="1.0"?><!DOCTYPE urlset SYSTEM "{dtd.as_uri()}">'
        "<urlset><url><loc>https://a.example/&inc;</loc></url></urlset>"
    )
    assert MARKER not in str(_read(document))
