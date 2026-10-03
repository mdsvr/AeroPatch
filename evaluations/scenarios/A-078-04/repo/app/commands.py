"""Command lines for the tools that the log viewer runs."""


def count_command(term, path):
    """`grep` call that prints how many lines of `path` contain `term` as plain text."""
    return f"grep -c -F -- {term} {path}"


def tail_command(path, lines):
    """`tail` call that prints the last `lines` lines of `path`."""
    return f"tail -n {int(lines)} {path}"


def size_command(path):
    """`wc` call that prints the size of `path` in bytes."""
    return f"wc -c {path}"
