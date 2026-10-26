"""ReDoS findings from regexploit (Phase B2 of reports/Real bug detection and model mix.md).

Regular expressions are read from the Python source (never run), with regexploit's own extractor and
its own threshold: cubic or worse backtracking. CPU only, no model, nothing written.
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

with warnings.catch_warnings():
    # ponytail: regexploit 1.0.0 imports sre_parse, deprecated since Python 3.11. It still works on
    # 3.13; if a Python release removes it, this import fails and the check needs another checker.
    warnings.simplefilter("ignore", DeprecationWarning)
    from regexploit.ast.sre import SreOpParser
    from regexploit.languages.python_node_visitor import PythonNodeVisitor
    from regexploit.redos import find

from aeropatch.contracts import Finding
from aeropatch.tools import scanners

RULE = "regexploit.redos"


def scan_file(repo: Path, rel: str) -> list[Finding]:
    try:
        tree = ast.parse((repo / rel).read_bytes())
    except (OSError, SyntaxError, ValueError, RecursionError):
        return []
    visitor = PythonNodeVisitor()
    try:
        visitor.visit(tree)
    except RecursionError:
        return []
    out = []
    for regex in visitor.patterns:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                worst = max((r.starriness for r in find(SreOpParser().parse_sre(regex.pattern, regex.flags))),
                            default=0)
            except Exception:  # noqa: BLE001, S112 - re.error and regexploit's own; one odd pattern must not stop the check
                continue
        if worst > 2:
            kind = "exponential" if worst > 10 else f"degree {worst}"
            out.append(Finding(
                tool="regexploit", rule_id=RULE, path=rel, line=regex.lineno, end_line=regex.lineno,
                cwe="CWE-1333", severity="medium",
                message=f"This regular expression can backtrack badly ({kind}) on crafted text.",
                fingerprint=scanners.fingerprint(RULE, rel, scanners._snippet(repo, rel, regex.lineno))))
    return out


def scan(repo: Path, files: list[str]) -> list[Finding]:
    return [f for rel in files for f in scan_file(repo, rel)]
