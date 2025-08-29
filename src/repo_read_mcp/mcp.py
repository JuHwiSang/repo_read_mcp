import os
from pydantic import BaseModel

from fastmcp import FastMCP, Context

# Safely join paths within the project root.
from .lib.utils import safe_path_join
from .seagoat import Seagoat
from .lib.fastmcp_progress_keepalive import ProgressKeepAlive
from .models import (
    FileChunk,
    ReadFilesOutput,
    ReadDirsOutput,
    DirTreeOutput,
    SearchResultsOutput,
)
from .repository import Repository

# FileReadTool, GlobTool, ReadDirTool 등은 FileSystemTools에 포함되어
# 더 이상 개별적으로 import하지 않습니다.


def make_mcp_server(name: str, project_path: str) -> FastMCP:
    """
    주어진 project_path에 대한 읽기 전용 도구를 제공하는 MCP 서버를 생성합니다.
    """
    mcp = FastMCP(name=name, instructions="""
                  This is a MCP server for reading a repository. Only read tools are available.
                  All tools continuously send pings to maintain the session.
                  """)
    repository = Repository(project_path)
    
    @mcp.tool(
        description="Read multiple files from the project.",
    )
    async def read_files(ctx: Context, file_paths: list[str]) -> ReadFilesOutput:
        """Return file contents with basic metadata.

        The result schema::

            {
                "file_path": <original file_path>,
                "start_line": 1,
                "end_line": <total number of lines>,
                "content": <entire file contents as a single string>
            }

        If the file does not exist, an ``error`` key will be returned instead.
        """
        async with ProgressKeepAlive(ctx):
            return repository.read_files(file_paths)
    
    @mcp.tool(
        description="Read a single file from the project.",
    )
    async def read_file_lines(ctx: Context, file_path: str, start_line: int, end_line: int) -> FileChunk:
        """Read a single file from the project."""
        async with ProgressKeepAlive(ctx):
            return repository.read_file_lines(file_path, start_line, end_line)
    
    @mcp.tool
    async def read_dirs(ctx: Context, dir_paths: list[str]) -> ReadDirsOutput:
        """List entries for multiple directories relative to the project root (non-recursive).

        The result schema::

            {
                "dirs": [
                    {
                        "dir_path": "src",
                        "entries": ["main.py", "utils"],
                        "error": null
                    },
                    ...
                ]
            }
        """
        async with ProgressKeepAlive(ctx):
            return repository.read_dirs(dir_paths)

    @mcp.tool(
        description="List directory entries relative to the project root. Max entries is 100.",
    )
    async def tree_dir(ctx: Context, dir_path: str, depth: int = 1) -> DirTreeOutput:
        """List directory entries relative to the project root. Max entries is 100."""
        async with ProgressKeepAlive(ctx):
            return repository.tree_dir(dir_path, depth)
    
    @mcp.tool(
        description="""Searches the repository using a natural language query. You can mix regular expressions with natural language.

**Query Examples:**

- **Natural Language:**
    - `"Where are the numbers rounded"`
- **Natural Language + Regex:**
    - `"function calc_.* that deals with taxes"`
    - `"function db_.* that initializes database"`
- **Regex:**
    - `"class .*Service implements .*Discount"`
    - `"function (get|create|update|delete)Category"`
    """
    )
    async def search(ctx: Context, query: str) -> SearchResultsOutput:
        """Search the repository using a natural-language query."""
        async with ProgressKeepAlive(ctx):
            return repository.search(query)
    
    return mcp
