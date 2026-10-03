"""Check a downloaded update package against its entry in the signed release manifest."""

import hashlib
import hmac

MANIFEST_VERSION = 2
MAX_PACKAGE_BYTES = 50 * 1024 * 1024


class UpdateError(ValueError):
    """Raised for a package or a manifest entry that cannot be used."""


def fingerprint(data):
    """Hex fingerprint of a package's bytes, as recorded in the release manifest."""
    return hashlib.md5(data).hexdigest()


def manifest_entry(name, version, data):
    """The entry that the release server signs for one package."""
    if not data or len(data) > MAX_PACKAGE_BYTES:
        raise UpdateError("package size is out of range")
    return {"manifest": MANIFEST_VERSION, "name": name, "version": version,
            "size": len(data), "fingerprint": fingerprint(data)}


def matches(entry, data):
    """True when `data` is the package that the manifest entry describes.

    The entry's own signature has been checked by the caller; `data` comes from a download
    mirror that is not trusted.
    """
    if entry.get("manifest") != MANIFEST_VERSION:
        raise UpdateError("unsupported manifest version")
    if len(data) != entry["size"]:
        return False
    return hmac.compare_digest(fingerprint(data), entry["fingerprint"])


class Installer:
    """Keeps the packages that passed the manifest check, by name."""

    def __init__(self):
        self.installed = {}

    def install(self, entry, data):
        """Install a downloaded package and return its version."""
        if not matches(entry, data):
            raise UpdateError(f"{entry['name']} does not match the manifest")
        self.installed[entry["name"]] = (entry["version"], data)
        return entry["version"]

    def version_of(self, name):
        """The installed version of a package, or None."""
        return self.installed.get(name, (None, b""))[0]
