"""Maintenance helpers for a directory of service logs."""

import os
import subprocess

LOG_SUFFIXES = (".log", ".out")
LEVELS = ("ERROR", "WARNING", "INFO")
MAX_TAIL_LINES = 500


def list_logs(directory):
    """Sorted names of the log files and log folders directly inside `directory`."""
    found = []
    for entry in os.scandir(directory):
        if entry.is_dir() or entry.name.endswith(LOG_SUFFIXES):
            found.append(entry.name)
    return sorted(found)


def tail(directory, name, lines=20):
    """Return the last `lines` lines of log file `name` as a list of strings."""
    lines = max(1, min(int(lines), MAX_TAIL_LINES))
    out = subprocess.run(
        ["tail", "-n", str(lines), "--", name], cwd=directory, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def level_counts(lines):
    """Count log lines per level, e.g. {"ERROR": 2, "WARNING": 0, "INFO": 5}."""
    counts = dict.fromkeys(LEVELS, 0)
    for line in lines:
        for level in LEVELS:
            if f" {level} " in f" {line} ":
                counts[level] += 1
                break
    return counts


def recent_errors(directory, name, lines=200):
    """Number of ERROR lines among the last `lines` lines of a log file."""
    return level_counts(tail(directory, name, lines))["ERROR"]


def usage_kb(directory, name):
    """Disk usage in kilobytes of the log file or log folder `name` inside `directory`.

    `name` is the entry an operator picked on the storage page.
    """
    out = subprocess.run(
        f"du -sk {name}", shell=True, cwd=directory, capture_output=True, text=True, check=True
    )
    return int(out.stdout.split()[0])


def largest(directory, top=3):
    """The `top` biggest logs as (name, kilobytes) pairs, biggest first."""
    sized = [(name, usage_kb(directory, name)) for name in list_logs(directory)]
    return sorted(sized, key=lambda pair: (-pair[1], pair[0]))[:top]


def over_quota(directory, quota_kb):
    """Names of the logs that use more than `quota_kb` kilobytes."""
    return [name for name in list_logs(directory) if usage_kb(directory, name) > quota_kb]
