"""Route selection: a plain function, not a class hierarchy (doc 04 §5)."""

from __future__ import annotations

from pathlib import Path

from aeropatch.models import fallback_client, local_client, oracle_client
from aeropatch.models.base import Generation


def generate(route: str, messages: list[dict], system: str, cfg: dict, temperature: float,
             scenario_dir: Path | None = None) -> Generation:
    if route == "local":
        return local_client.generate(messages, system, cfg, temperature)
    if route == "frontier":
        return fallback_client.generate(messages, system, cfg, temperature)
    if route == "oracle":
        return oracle_client.generate(scenario_dir)
    raise ValueError(f"unknown route {route!r}")


def model_name(route: str, cfg: dict) -> str:
    return {"local": cfg["local_model"], "frontier": cfg["frontier_model"]}.get(route, route)
