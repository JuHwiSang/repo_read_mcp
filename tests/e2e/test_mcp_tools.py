import os
import shutil
import tempfile

import pytest

from repo_read_mcp.mcp import make_mcp_server

# FastMCP imports – the public API is stable across v2.x
from fastmcp import Client

# Shared test helpers
from tests.helpers import create_git_repo, remove_readonly

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def temp_repo():
    """Create a temporary git repository for the duration of the test module."""
    test_dir = tempfile.mkdtemp()
    create_git_repo(test_dir)
    yield test_dir
    shutil.rmtree(test_dir, onexc=remove_readonly)


@pytest.fixture(scope="module")
def mcp_server(temp_repo):
    """Return an in-process FastMCP server bound to the temporary repo."""
    return make_mcp_server(name="test-mcp-server", project_path=temp_repo)


# ---------------------------------------------------------------------------
# E2E test cases for the four core tools defined in repo_read_mcp.mcp
# ---------------------------------------------------------------------------


async def test_read_files(mcp_server):
    async with Client(mcp_server) as client:
        resp = await client.call_tool(
            "read_files",
            {"file_paths": ["sample.py", "another.py"]},
        )

    # The result schema is defined by ReadFilesOutput – we expect a dict with a
    # "files" key that is a list of file-chunk dicts.
    assert isinstance(resp.structured_content, dict), "Expected response to be a dict"
    assert "files" in resp.structured_content, "Response missing 'files' key"

    files = {chunk["file_path"]: chunk for chunk in resp.structured_content["files"]}
    assert "sample.py" in files and "another.py" in files

    # Basic content sanity checks
    assert "def hello_world" in files["sample.py"]["content"]
    assert "class Greeter" in files["another.py"]["content"]



async def test_read_file_lines(mcp_server):
    # Read just the first line of sample.py
    async with Client(mcp_server) as client:
        resp = await client.call_tool(
            "read_file_lines",
            {"file_path": "sample.py", "start_line": 1, "end_line": 1},
        )

    assert isinstance(resp.structured_content, dict)
    assert resp.structured_content.get("content", "").startswith("def hello_world()")
    assert resp.structured_content.get("start_line") == 1
    assert resp.structured_content.get("end_line") == 1



async def test_read_dir(mcp_server):
    async with Client(mcp_server) as client:
        resp = await client.call_tool("read_dir", {"dir_path": ""})

    # DirEntriesOutput -> dict with "dir_path" and "entries" keys
    assert isinstance(resp.structured_content, dict), "Expected response to be a dict"
    assert resp.structured_content.get("dir_path") == ""

    entries = resp.structured_content.get("entries", [])
    assert "sample.py" in entries
    assert "another.py" in entries



async def test_tree_dir(mcp_server):
    async with Client(mcp_server) as client:
        resp = await client.call_tool("tree_dir", {"dir_path": "", "depth": 1})

    # DirTreeOutput -> dict with "tree" key containing list[str]
    assert isinstance(resp.structured_content, dict), "Expected response to be a dict"

    tree = resp.structured_content.get("tree", [])

    # First element should be the root dir path (empty string in this case)
    assert tree and tree[0] == ""

    # Verify that our files appear somewhere in the tree listing
    assert any(p.endswith("sample.py") for p in tree)
    assert any(p.endswith("another.py") for p in tree)
