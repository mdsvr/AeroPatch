"""Read members of a zip over HTTP range requests, so a few folders of a 6 GB archive can be taken
without downloading all of it (Phase A of reports/Real bug detection and model mix.md).

    python evaluations/tools/remote_zip.py URL                 # list top-level folders and sizes
    python evaluations/tools/remote_zip.py URL PREFIX... --to DIR  # extract members under PREFIXes
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


class RangeFile(io.RawIOBase):
    """A seekable read-only file over HTTP range requests (the server must answer 206)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=0-0"})) as r:
            self.size = int(r.headers["Content-Range"].rsplit("/", 1)[1])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, b):
        if self.pos >= self.size or not len(b):
            return 0
        end = min(self.pos + len(b), self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)


def open_zip(url: str) -> zipfile.ZipFile:
    # A large buffer: zipfile reads members in small pieces, one request each without it.
    return zipfile.ZipFile(io.BufferedReader(RangeFile(url), buffer_size=4 << 20))


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("prefixes", nargs="*")
    p.add_argument("--to", type=Path)
    p.add_argument("--depth", type=int, default=1, help="folder depth to list")
    a = p.parse_args(argv)
    zf = open_zip(a.url)
    if not a.prefixes:
        sizes = Counter()
        for i in zf.infolist():
            sizes["/".join(PurePosixPath(i.filename).parts[:a.depth])] += i.file_size
        for k, v in sorted(sizes.items()):
            print(f"{v / 1e6:10.1f} MB  {k}")
        return 0
    if a.to is None:
        p.error("--to is required with prefixes")
    root = a.to.resolve()
    for i in zf.infolist():
        if i.is_dir() or not i.filename.startswith(tuple(a.prefixes)):
            continue
        dest = (root / i.filename).resolve()
        if not dest.is_relative_to(root):  # a member named ../x would land outside --to
            print(f"skipped {i.filename}", file=sys.stderr)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(i) as src, open(dest, "wb") as out:
            out.write(src.read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
