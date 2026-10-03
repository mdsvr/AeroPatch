"""MCP server: a thin stdio wrapper over the tool functions (doc 06 §2-4).

    uv run aeropatch mcp

The real logic lives in `aeropatch.tools`, `aeropatch.sandbox` and `aeropatch.agent`; this file
only checks the client's input and registers the functions. There is no commit, push or PR tool.

Arguments from the client are a trust boundary (doc 13, T8): `repo` must sit under an
allowlisted root, `path` inside `repo`, and `task_id` must name a benchmark scenario. Errors go
back as short messages; tracebacks and host paths do not.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from aeropatch import scenario
from aeropatch.agent import gates, loop
from aeropatch.config import SCENARIOS_DIR, load_config
from aeropatch.sandbox import sandbox
from aeropatch.tools import context, scanners
from aeropatch.tools.git_ops import Workspace
from aeropatch.tools.paths import PathError, check_under_roots

MAX_DIFF_BYTES = 64_000
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

server = MCPServer("aeropatch", instructions=(
    "Security-fix tools for Python repositories. Results are candidate fixes that need human "
    "review. Nothing here commits, pushes or opens pull requests."))


def _guard(fn):
    """Turn expected errors into short tool errors and hide everything else behind its type name."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ToolError, PathError, scenario.ScenarioError) as e:
            raise ToolError(str(e)) from None
        except Exception as e:  # noqa: BLE001 - the message may hold host paths
            raise ToolError(f"internal error: {type(e).__name__}") from None
    return wrapper


def _repo(repo: str) -> Path:
    """The scenario directory, plus roots listed in AEROPATCH_MCP_ROOTS (os.pathsep-separated)."""
    extra = [Path(p) for p in os.environ.get("AEROPATCH_MCP_ROOTS", "").split(os.pathsep) if p]
    try:
        path = check_under_roots(Path(repo), [SCENARIOS_DIR, *extra])
    except PathError:
        raise PathError("repo is not under an allowlisted root") from None
    if not path.is_dir():
        raise PathError("repo is not a directory")
    return path


def _task(task_id: str):
    if task_id not in scenario.list_ids():  # also keeps "../x" out of scenario.load
        raise ToolError("unknown task_id")
    scenario.ensure_image(task_id)
    return scenario.load(task_id)


@server.tool(annotations=READ_ONLY)
@_guard
def scan(repo: str) -> list[dict]:
    """Run Opengrep and Bandit on a repository and return the normalized findings."""
    return [f.to_dict() for f in scanners.scan(_repo(repo))["findings"]]


@server.tool(annotations=READ_ONLY)
@_guard
def get_context(repo: str, path: str, line: int) -> dict:
    """Scoped code context for a finding at path:line (enclosing function, imports, call sites)."""
    return context.get_context(_repo(repo), path, line).to_dict()


@server.tool(annotations=READ_ONLY)
@_guard
def validate(task_id: str, diff: str) -> dict:
    """Check a unified diff against a benchmark scenario: safety gates, then the PoC and
    regression tests in the sandbox. Works on a scratch copy; nothing on the host changes."""
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise ToolError(f"diff is larger than {MAX_DIFF_BYTES} bytes")
    task = _task(task_id)
    with Workspace(task.repo_path) as ws:
        files = {p for p in ws.repo.rglob("*") if p.is_file()}
        originals = ws.read_many(task.allowed_paths)
        if ws.apply_patch(diff):
            raise ToolError("the diff does not apply to the scenario")
        if {p for p in ws.repo.rglob("*") if p.is_file()} != files:
            raise ToolError("the diff may not add or remove files")  # new files skip the gates
        gate = gates.check(originals, ws.read_many(ws.changed_paths()), task.allowed_paths,
                           allow_imports=task.allow_imports)
        if not gate.ok:
            return {"resolved": False, "gate": gate.to_dict(), "sandbox": None}
        result = sandbox.run_tests(task.image, ws.src)
    return {"resolved": result.resolved, "gate": gate.to_dict(), "sandbox": result.to_dict()}


@server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
@_guard
def remediate(task_id: str, config: str = "repair-local") -> dict:
    """Run the full remediation loop on a benchmark scenario and return the outcome with the
    candidate diff. Calls the model route of the named config, which may be a remote API."""
    task = _task(task_id)
    try:
        cfg = load_config(config)
    except KeyError:
        raise ToolError("unknown config") from None
    result = loop.run(task, cfg)
    return {"task_id": task_id, "resolved": result.resolved, "label": result.label,
            "attempts": [{"n": a.n, "route": a.route, "label": a.label} for a in result.attempts],
            "diff": result.final_diff, "duration_s": result.duration_s}
