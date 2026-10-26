"""Known-vulnerable pinned packages, from the OSV database (Phase B1 of reports/Real bug detection
and model mix.md).

Reads `name==version` pins from requirements*.txt and pyproject.toml at the folder's top level and
asks api.osv.dev about them: package names and versions leave the laptop, no code does. Nothing is
installed, built or written. The result is a fixed card per package; the model never edits a pin
(requirements files are in FORBIDDEN_GLOBS), so the user makes the one-line change.
"""

from __future__ import annotations

import json
import re
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import InvalidVersion, Version

OSV = "https://api.osv.dev/v1"
TIMEOUT_S = 15
PIN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9][A-Za-z0-9.+!_-]*)")
# Distributions whose import name differs from the normalised project name.
IMPORT_NAMES = {"pyjwt": "jwt", "pyyaml": "yaml", "pillow": "PIL", "beautifulsoup4": "bs4",
                "scikit-learn": "sklearn", "python-dateutil": "dateutil", "opencv-python": "cv2",
                "protobuf": "google.protobuf", "pycryptodome": "Crypto", "python-jose": "jose",
                "python-multipart": "multipart", "msgpack-python": "msgpack", "attrs": "attr"}


@dataclass
class Pin:
    name: str
    version: str
    path: str  # where it is pinned, relative to the folder
    line: int


@dataclass
class Advisory:
    pin: Pin
    ids: list[str]  # OSV ids, with CVE aliases first where there are any
    summary: str
    fixed: str  # the lowest fixed version above the pinned one; "" when none is published
    imported_in: list[str] = field(default_factory=list)  # files that import the package


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins(folder: Path) -> list[Pin]:
    pins = []
    for req in sorted(folder.glob("requirements*.txt")):
        for n, line in enumerate(req.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = PIN.match(line.split("#", 1)[0].split(";", 1)[0])
            if m:
                pins.append(Pin(_norm(m[1]), m[2], req.name, n))
    pyproject = folder / "pyproject.toml"
    if pyproject.is_file():
        try:
            deps = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("dependencies", [])
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, AttributeError):
            deps = []
        lines = pyproject.read_text(encoding="utf-8", errors="replace").splitlines()
        for dep in deps if isinstance(deps, list) else []:
            m = PIN.match(str(dep).split(";", 1)[0])
            if m:
                line = next((i for i, text in enumerate(lines, 1) if str(dep) in text), 1)
                pins.append(Pin(_norm(m[1]), m[2], "pyproject.toml", line))
    seen = set()  # one entry per package and version, the first place it is pinned
    return [p for p in pins if (p.name, p.version) not in seen and not seen.add((p.name, p.version))]


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.load(r)


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=TIMEOUT_S) as r:
        return json.load(r)


def _fixed_above(vuln: dict, name: str, version: str) -> str:
    try:
        current = Version(version)
    except InvalidVersion:
        return ""
    fixed = []
    for aff in vuln.get("affected", []):
        if _norm(aff.get("package", {}).get("name", "")) != name:
            continue
        for rng in aff.get("ranges", []):
            for ev in rng.get("events", []):
                try:
                    if "fixed" in ev and Version(ev["fixed"]) > current:
                        fixed.append(Version(ev["fixed"]))
                except InvalidVersion:
                    pass
    return str(min(fixed)) if fixed else ""


def _importers(folder: Path, name: str, py_files: list[str]) -> list[str]:
    module = IMPORT_NAMES.get(name, name.replace("-", "_"))
    pat = re.compile(rf"^\s*(?:import|from)\s+{re.escape(module)}(?:[\s.,]|$)", re.MULTILINE)
    hits = []
    for rel in py_files:
        try:
            if pat.search((folder / rel).read_text(encoding="utf-8", errors="replace")):
                hits.append(rel)
        except OSError:
            pass
    return hits


def audit(folder: Path, py_files: list[str], post=_post, get=_get) -> tuple[list[Advisory], int, str]:
    """(advisories, pins looked up, error). The error is "" or a plain sentence; on any network
    failure nothing is reported, never a guess."""
    pins = read_pins(folder)
    if not pins:
        return [], 0, ""
    queries = [{"package": {"name": p.name, "ecosystem": "PyPI"}, "version": p.version} for p in pins]
    try:
        results = post(f"{OSV}/querybatch", {"queries": queries}).get("results", [])
        all_ids = sorted({v["id"] for res in results for v in res.get("vulns", [])})
        with ThreadPoolExecutor(8) as pool:  # one request per advisory; sequential took 20 s for 3 packages
            details = dict(zip(all_ids, pool.map(lambda i: get(f"{OSV}/vulns/{i}"), all_ids), strict=True))
        out = []
        for pin, res in zip(pins, results, strict=False):
            ids = [v["id"] for v in res.get("vulns", [])]
            if not ids:
                continue
            vulns = [details[i] for i in ids]
            names = []
            for v in vulns:
                cves = [a for a in v.get("aliases", []) if a.startswith("CVE-")]
                names += [n for n in (cves or [v["id"]]) if n not in names]
            fixes = [f for f in (_fixed_above(v, pin.name, pin.version) for v in vulns) if f]
            summary = next((v.get("summary", "") for v in vulns if v.get("summary")), "")
            # One version must fix them all; none when any advisory has no fix published.
            out.append(Advisory(pin=pin, ids=names, summary=summary,
                                fixed=str(max(map(Version, fixes))) if len(fixes) == len(vulns) else "",
                                imported_in=_importers(folder, pin.name, py_files)))
        return out, len(pins), ""
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
        return [], len(pins), f"The advisory lookup at osv.dev did not answer ({type(e).__name__}), so pinned packages were not checked."
