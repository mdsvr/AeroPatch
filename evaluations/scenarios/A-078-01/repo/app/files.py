"""Small file utilities for the notes service."""

import subprocess


def count_lines(directory, filename):
    """Return the number of lines in `filename` inside `directory`."""
    out = subprocess.run(
        f"wc -l < {filename}", shell=True, cwd=directory, capture_output=True, text=True, check=True
    )
    return int(out.stdout.strip())
