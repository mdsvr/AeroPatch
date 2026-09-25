"""Turn pytest JUnit XML into a compact failure summary for the model (doc 07 §7)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # nosec B405 - parses our own sandbox output, size-capped

from aeropatch.contracts import Failure

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
WORK_RE = re.compile(r"/work/(repo/|tests_poc/|tests_regression/)?")


def clean(text: str) -> str:
    text = ANSI_RE.sub("", text)
    return WORK_RE.sub(lambda m: m.group(1) or "", text)


def trim_trace(text: str, keep: int = 15) -> str:
    """Drop site-packages frames, keep the last `keep` lines."""
    lines = [line for line in clean(text).splitlines() if "site-packages" not in line]
    return "\n".join(lines[-keep:])


def parse(xml_text: str) -> tuple[int, list[Failure]]:
    """Return (tests run, failures). Malformed/missing XML counts as zero tests."""
    if not xml_text.strip():
        return 0, []
    try:
        root = ET.fromstring(xml_text)  # nosec B314
    except ET.ParseError:
        return 0, [Failure(test_id="<junit>", kind="error", message="unreadable JUnit XML")]
    total = 0
    failures: list[Failure] = []
    for case in root.iter("testcase"):
        total += 1
        name = ".".join(p for p in (case.get("classname", ""), case.get("name", "")) if p)
        for kind in ("failure", "error"):
            el = case.find(kind)
            if el is not None:
                failures.append(Failure(
                    test_id=clean(name),
                    kind=kind,
                    message=clean(el.get("message", ""))[:500],
                    trace=trim_trace(el.text or ""),
                ))
        if case.find("skipped") is not None:
            failures.append(Failure(test_id=clean(name), kind="skipped", message="test was skipped"))
    return total, failures


def classify(failures: list[Failure]) -> str:
    """Most specific label for a set of failures from one suite."""
    blob = "\n".join(f"{f.message}\n{f.trace}" for f in failures)
    if "pytest-timeout" in blob or "Timeout (>" in blob:
        return "TIMEOUT"
    if "SyntaxError" in blob or "IndentationError" in blob:
        return "SYNTAX_ERROR"
    if "ImportError" in blob or "ModuleNotFoundError" in blob:
        return "IMPORT_ERROR"
    if any(f.message.startswith("collection failure") for f in failures):
        return "COLLECTION_ERROR"
    return ""


def summarize(failures: list[Failure], char_cap: int = 6000) -> str:
    """Repair context: failed test IDs, messages and trimmed traces, capped (~1.5k tokens)."""
    parts = []
    for f in failures:
        parts.append(f"FAILED {f.test_id}: {f.message}".strip())
        if f.trace:
            parts.append(f.trace)
    text = "\n".join(parts)
    if len(text) > char_cap:
        text = text[: char_cap - 20] + "\n...[truncated]"
    return text
