"""Download output files of the kernel's newest version, streamed to disk.

    uv run --no-project --with kaggle python training/kaggle/fetch_output.py <regex> <folder>

`kaggle kernels output` reads each file into memory before it writes it, and a GGUF is 2.8 GB on a
laptop with 16 GB. This asks the same API for the file list and streams the files whose path
matches the regular expression, keeping their folders. A file already there at full size is skipped.
"""

import json
import os
import re
import sys

import requests
from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest, KaggleApi

HERE = os.path.dirname(os.path.abspath(__file__))


def main(pattern: str, folder: str) -> None:
    with open(os.path.join(HERE, "kernel-metadata.json"), encoding="utf-8") as f:
        owner, slug = json.load(f)["id"].split("/")
    api = KaggleApi()
    api.authenticate()
    token, seen = None, 0
    while True:
        with api.build_kaggle_client() as kaggle:
            request = ApiListKernelSessionOutputRequest()
            request.user_name, request.kernel_slug = owner, slug
            if token:
                request.page_token = token
            response = kaggle.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            if not re.search(pattern, item.file_name):
                continue
            seen += 1
            dest = os.path.join(folder, *item.file_name.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with requests.get(item.url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                if total and os.path.exists(dest) and os.path.getsize(dest) == total:
                    print(f"have {item.file_name}", flush=True)
                    continue
                done = 0
                with open(dest + ".part", "wb") as out:
                    for chunk in r.iter_content(1 << 20):
                        out.write(chunk)
                        done += len(chunk)
            if total and done != total:
                sys.exit(f"{item.file_name}: {done} of {total} bytes")
            os.replace(dest + ".part", dest)
            print(f"downloaded {item.file_name} ({done / 1e6:.1f} MB)", flush=True)
        token = response.next_page_token
        if not token:
            break
    if not seen:
        sys.exit(f"no output file matches {pattern!r}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
