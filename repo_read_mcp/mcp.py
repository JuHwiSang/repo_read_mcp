import os

from fastmcp import FastMCP

# Safely join paths within the project root.
from .lib.utils import safe_path_join
from .semantic import SemanticSearch

# FileReadTool, GlobTool, ReadDirTool 등은 FileSystemTools에 포함되어
# 더 이상 개별적으로 import하지 않습니다.


def make_mcp_server(name: str, project_path: str) -> FastMCP:
    """
    주어진 project_path에 대한 읽기 전용 도구를 제공하는 MCP 서버를 생성합니다.
    """
    mcp = FastMCP(name=name)
    semantic = SemanticSearch(project_path)
    
    @mcp.tool
    def read_files(file_paths: list[str]) -> list[dict]:
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

        results = []
        for file_path in file_paths:
            try:
                abs_path = safe_path_join(project_path, file_path)
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                results.append({
                    "file_path": file_path,
                    "start_line": 1,
                    "end_line": len(lines),
                    "content": "".join(lines),
                })

            except FileNotFoundError:
                results.append({
                    "file_path": file_path,
                    "error": f"File not found: {file_path}",
                })
            except Exception as e:
                results.append({
                    "file_path": file_path,
                    "error": f"Error reading file: {e}",
                })

        return results
    
    @mcp.tool
    def read_dir(dir_path: str) -> list[str]:
        """List directory entries relative to the project root."""
        try:
            return os.listdir(safe_path_join(project_path, dir_path))
        except Exception as e:
            return [f"Error reading directory: {e}"]

    @mcp.tool(
        description="List directory entries relative to the project root. Max entries is 100.",
    )
    def tree_dir(dir_path: str, depth: int = 2) -> list[str]:
        """List directory entries relative to the project root. Max entries is 100."""
        results = []
        root_path = safe_path_join(project_path, dir_path)
        
        # Limit total entries to 100
        max_entries = 100

        def _walk(current_path, current_depth):
            if len(results) >= max_entries:
                return

            if current_depth > depth:
                return
            
            try:
                with os.scandir(current_path) as it:
                    for entry in it:
                        if len(results) >= max_entries:
                            return
                        
                        # Get path relative to the initial dir_path
                        relative_to_start_dir = os.path.relpath(entry.path, root_path)
                        # Prepend original dir_path to get path relative to project root
                        result_path = os.path.join(dir_path, relative_to_start_dir)

                        results.append(result_path)

                        if entry.is_dir():
                            _walk(entry.path, current_depth + 1)
            except FileNotFoundError:
                # This could happen if a directory is deleted during the walk
                pass
            except Exception as e:
                # Log or handle other potential errors if necessary
                # For now, we just stop walking this path
                pass

        try:
            if not os.path.isdir(root_path):
                 return [f"Error: Directory not found at '{dir_path}'"]
            results.append(dir_path) # Add the root of the tree itself
            _walk(root_path, 1)
        except Exception as e:
            return [f"Error processing directory '{dir_path}': {e}"]

        return results[:max_entries]
    
    @mcp.tool
    def natural_language_search(query: str) -> list[str]:
        """Search for files in the project."""
        return semantic.search(query)
    
    return mcp
