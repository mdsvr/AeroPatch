import re

import pytest

from app.updates import Installer, UpdateError, fingerprint, manifest_entry, matches

PACKAGE = b"agent build 2.4.1\n" * 500


def test_fingerprint_is_a_stable_hex_string():
    assert fingerprint(PACKAGE) == fingerprint(bytes(PACKAGE))
    assert re.fullmatch(r"[0-9a-f]{32,}", fingerprint(PACKAGE))
    assert fingerprint(PACKAGE) != fingerprint(PACKAGE + b"\n")
    assert fingerprint(b"") != fingerprint(b"\x00")


def test_manifest_entry_describes_the_package():
    entry = manifest_entry("agent", "2.4.1", PACKAGE)
    assert entry["name"] == "agent" and entry["version"] == "2.4.1"
    assert entry["size"] == len(PACKAGE) and entry["manifest"] == 2
    assert entry["fingerprint"] == fingerprint(PACKAGE)


def test_released_package_matches_its_entry():
    assert matches(manifest_entry("agent", "2.4.1", PACKAGE), PACKAGE) is True


def test_changed_or_truncated_package_does_not_match():
    entry = manifest_entry("agent", "2.4.1", PACKAGE)
    assert matches(entry, PACKAGE[:-1] + b"!") is False
    assert matches(entry, PACKAGE[:-1]) is False
    assert matches(entry, PACKAGE + b"extra") is False


def test_bad_inputs_raise():
    with pytest.raises(UpdateError):
        manifest_entry("agent", "2.4.1", b"")
    entry = manifest_entry("agent", "2.4.1", PACKAGE)
    with pytest.raises(UpdateError):
        matches({**entry, "manifest": 1}, PACKAGE)


def test_installer_installs_and_updates():
    installer = Installer()
    assert installer.version_of("agent") is None
    assert installer.install(manifest_entry("agent", "2.4.1", PACKAGE), PACKAGE) == "2.4.1"
    newer = PACKAGE + b"hotfix\n"
    assert installer.install(manifest_entry("agent", "2.4.2", newer), newer) == "2.4.2"
    assert installer.version_of("agent") == "2.4.2"
    assert installer.installed["agent"] == ("2.4.2", newer)


def test_installer_keeps_the_old_version_when_a_download_is_corrupt():
    installer = Installer()
    installer.install(manifest_entry("agent", "2.4.1", PACKAGE), PACKAGE)
    newer = PACKAGE + b"hotfix\n"
    with pytest.raises(UpdateError):
        installer.install(manifest_entry("agent", "2.4.2", newer), newer[:-7] + b"garbage")
    assert installer.version_of("agent") == "2.4.1"
