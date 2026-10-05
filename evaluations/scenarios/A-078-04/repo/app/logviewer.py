"""Log viewer backend: search, tail and size the service logs in one directory."""

import os
import subprocess

from app.commands import count_command, size_command, tail_command

LOG_NAMES = ("app.log", "worker.log", "audit.log")
TIMEOUT_SECONDS = 10


class LogError(ValueError):
    """Raised when a log cannot be read or a tool fails."""


def _log_path(log_dir, name):
    """Path of one of the known logs."""
    if name not in LOG_NAMES:
        raise LogError(f"unknown log {name!r}")
    return os.path.join(log_dir, name)


def run_tool(command):
    """Run one of the commands from app/commands.py and return (exit status, stdout)."""
    proc = subprocess.run(command, shell=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=TIMEOUT_SECONDS)
    return proc.returncode, proc.stdout


def count_matches(log_dir, name, term):
    """How many lines of a log contain `term`, the text typed into the search box."""
    status, out = run_tool(count_command(term, _log_path(log_dir, name)))
    if status not in (0, 1):  # grep exits with 1 when no line matches
        raise LogError("search failed")
    return int(out.strip() or 0)


def last_lines(log_dir, name, lines=10):
    """The last `lines` lines of a log, oldest first."""
    status, out = run_tool(tail_command(_log_path(log_dir, name), lines))
    if status != 0:
        raise LogError("cannot read the log")
    return out.splitlines()


def size_bytes(log_dir, name):
    """Size of a log in bytes."""
    status, out = run_tool(size_command(_log_path(log_dir, name)))
    if status != 0:
        raise LogError("cannot read the log")
    return int(out.split()[0])
