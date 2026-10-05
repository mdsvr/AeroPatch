import contextlib

from app.updates import Installer, manifest_entry, matches

# Two different 128-byte blocks that a collision-prone digest cannot tell apart (a published
# pair). A mirror that holds the released block can serve the other one in its place.
RELEASED = bytes.fromhex(
    "d131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f89"
    "55ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5b"
    "d8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0"
    "e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70")
SWAPPED = bytes.fromhex(
    "d131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f89"
    "55ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5b"
    "d8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0"
    "e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70")
REST = b"\x00rest of the package, the same in both\n" * 40


def test_swapped_block_does_not_match_the_manifest():
    assert RELEASED != SWAPPED
    entry = manifest_entry("agent", "2.4.1", RELEASED)
    assert not matches(entry, SWAPPED)


def test_installer_refuses_a_package_built_on_the_swapped_block():
    entry = manifest_entry("agent", "2.4.1", RELEASED + REST)
    installer = Installer()
    with contextlib.suppress(Exception):  # how the package is refused is up to the fix
        installer.install(entry, SWAPPED + REST)
    assert installer.installed == {}
