"""The MCP wrapper: tool list, one real call, and the input checks at the boundary (doc 13, T8)."""

import asyncio

import pytest
from conftest import needs_docker
from mcp import Client

from aeropatch.config import ROOT, SCENARIOS_DIR
from aeropatch.mcp_server import MAX_DIFF_BYTES, server

REPO = str(SCENARIOS_DIR / "A-089-01" / "repo")


def call(tool: str, **args):
    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, args)
    return asyncio.run(go())


def test_tool_list_is_small_and_has_no_write_tools():
    async def go():
        async with Client(server) as client:
            return (await client.list_tools()).tools
    tools = {t.name: t for t in asyncio.run(go())}
    assert sorted(tools) == ["get_context", "remediate", "scan", "validate"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert tools["remediate"].annotations.open_world_hint is True


def test_get_context_serves_a_real_call():
    result = call("get_context", repo=REPO, path="app/db.py", line=12)
    assert not result.is_error
    assert "find_user" in result.content[0].text


@pytest.mark.parametrize("tool, args", [
    ("get_context", {"repo": str(ROOT), "path": "NOTES.md", "line": 1}),  # not an allowlisted root
    ("scan", {"repo": str(SCENARIOS_DIR / "A-089-01" / "repo" / ".." / ".." / ".." / "..")}),
    ("get_context", {"repo": REPO, "path": "../scenario.json", "line": 1}),  # traversal
    ("get_context", {"repo": REPO, "path": str(ROOT / "NOTES.md"), "line": 1}),  # absolute path
    ("validate", {"task_id": "../A-089-01", "diff": ""}),
    ("validate", {"task_id": "A-089-01", "diff": "x" * (MAX_DIFF_BYTES + 1)}),
    ("remediate", {"task_id": "no-such-task"}),
])
def test_bad_input_is_refused_without_leaking_host_paths(tool, args):
    result = call(tool, **args)
    assert result.is_error
    assert str(ROOT) not in result.content[0].text and "Traceback" not in result.content[0].text


@needs_docker[0]
@needs_docker[1]
def test_validate_runs_the_reference_fix_and_refuses_new_files():
    patch = (SCENARIOS_DIR / "A-089-01" / "reference_fix.patch").read_text(encoding="utf-8")
    result = call("validate", task_id="A-089-01", diff=patch)
    assert not result.is_error and '"resolved": true' in result.content[0].text.lower()

    new_file = ("diff --git a/sitecustomize.py b/sitecustomize.py\nnew file mode 100644\n--- /dev/null\n"
                "+++ b/sitecustomize.py\n@@ -0,0 +1 @@\n+print('hi')\n")
    result = call("validate", task_id="A-089-01", diff=new_file)
    assert result.is_error and "add or remove files" in result.content[0].text
