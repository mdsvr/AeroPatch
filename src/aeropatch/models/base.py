"""Common result type for every model route."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Generation:
    text: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    cost_usd: float = 0.0
    refusal: dict | None = None  # {provider, category, explanation}
    error: str = ""  # PROVIDER_ERROR detail


class LocalServerDown(RuntimeError):
    """Local model server unreachable: fail fast, never silently escalate (doc 08 part 2, §4)."""
