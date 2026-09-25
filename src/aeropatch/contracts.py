"""Shared data contracts (doc 05 §4). Plain dataclasses with to_json()."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


class _Json:
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)


@dataclass
class Finding(_Json):
    tool: str
    rule_id: str
    path: str
    line: int
    end_line: int = 0
    cwe: str = ""
    severity: str = "medium"
    message: str = ""
    fingerprint: str = ""


@dataclass
class Task(_Json):
    id: str
    repo_path: Path
    cwe: str
    finding: Finding
    description: str
    allowed_paths: list[str]
    poc_tests: list[str] = field(default_factory=list)
    regression_tests: list[str] = field(default_factory=list)
    image: str = ""
    # Ground-truth function (qualified name) for oracle localization and LOCALIZATION_MISS.
    target_function: str = ""
    allow_imports: list[str] = field(default_factory=list)


@dataclass
class Context(_Json):
    files: dict[str, str]  # path -> rendered snippet (header lines + code, no line prefixes)
    token_count: int
    target: str = ""  # qualified name of the enclosing function, if any


@dataclass
class Edit(_Json):
    path: str
    search: str
    replace: str


@dataclass
class EditProposal(_Json):
    edits: list[Edit]
    rationale: str = ""
    model: str = ""
    raw: str = ""
    usage: dict = field(default_factory=dict)
    parse_error: str = ""


@dataclass
class GateResult(_Json):
    ok: bool
    violations: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass
class Failure(_Json):
    test_id: str
    kind: str  # failure | error | skipped
    message: str
    trace: str = ""


@dataclass
class SandboxResult(_Json):
    applied: bool
    poc_passed: bool = False
    regressions_passed: bool = False
    poc_total: int = 0
    regression_total: int = 0
    lint_ok: bool = True
    rescan_clean: bool | None = None
    failures: list[Failure] = field(default_factory=list)
    label: str = ""  # RESOLVED | POC_FAIL | REGRESSION | IMPORT_ERROR | SYNTAX_ERROR | TIMEOUT | ...
    duration_s: float = 0.0
    timed_out: bool = False
    apply_error: str = ""

    @property
    def resolved(self) -> bool:
        return self.applied and self.poc_passed and self.regressions_passed


@dataclass
class Attempt(_Json):
    n: int
    route: str
    model: str = ""
    proposal: EditProposal | None = None
    apply_error: str = ""
    diff: str = ""
    gate: GateResult | None = None
    sandbox: SandboxResult | None = None
    label: str = ""
    latency_s: float = 0.0
    cost_usd: float = 0.0
    refusal: dict | None = None


@dataclass
class RunResult(_Json):
    task_id: str
    config: str
    attempts: list[Attempt]
    resolved: bool
    label: str
    final_diff: str = ""
    duration_s: float = 0.0
