import os
from pydantic import BaseModel

from fastmcp import FastMCP

# Safely join paths within the project root.
from .lib.utils import safe_path_join
from .seagoat import Seagoat

# FileReadTool, GlobTool, ReadDirTool 등은 FileSystemTools에 포함되어
# 더 이상 개별적으로 import하지 않습니다.

class FileChunk(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    content: str
    error: str | None = None
    
class ReadFilesOutput(BaseModel):
    files: list[FileChunk]
    error: str | None = None
    
class DirEntriesOutput(BaseModel):
    """Pydantic model representing a simple directory listing."""
    dir_path: str
    entries: list[str]
    error: str | None = None

class DirTreeOutput(BaseModel):
    """Pydantic model representing a directory tree walk limited by depth."""
    dir_path: str
    tree: list[str]
    error: str | None = None

class SearchResult(BaseModel):
    file: str
    start_line: int
    end_line: int
    code: str

class SearchResultsOutput(BaseModel):
    results: list[SearchResult]
    error: str | None = None

def make_mcp_server(name: str, project_path: str) -> FastMCP:
    """
    주어진 project_path에 대한 읽기 전용 도구를 제공하는 MCP 서버를 생성합니다.
    """
    mcp = FastMCP(name=name)
    seagoat = Seagoat(project_path)
    
    @mcp.tool(
        description="Read multiple files from the project.",
    )
    def read_files(file_paths: list[str]) -> ReadFilesOutput:
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

        results: list[FileChunk] = []
        for file_path in file_paths:
            try:
                abs_path = safe_path_join(project_path, file_path)
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                results.append(FileChunk(
                    file_path=file_path,
                    start_line=1,
                    end_line=len(lines),
                    content="".join(lines),
                ))

            except FileNotFoundError:
                results.append(FileChunk(
                    file_path=file_path,
                    start_line=0,
                    end_line=0,
                    content="",
                    error=f"File not found: {file_path}",
                ))
            except Exception as e:
                results.append(FileChunk(
                    file_path=file_path,
                    start_line=0,
                    end_line=0,
                    content="",
                    error=f"Error reading file: {e}",
                ))

        return ReadFilesOutput(files=results)
    
    @mcp.tool(
        description="Read a single file from the project.",
    )
    def read_file_lines(file_path: str, start_line: int, end_line: int) -> FileChunk:
        """Read a single file from the project."""
        try:
            abs_path = safe_path_join(project_path, file_path)
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Adjust line numbers to be within bounds
            start = max(1, min(start_line, len(lines)))
            end = max(start, min(end_line, len(lines)))
            
            selected_lines = lines[start-1:end]

            return FileChunk(
                file_path=file_path,
                start_line=start,
                end_line=end,
                content="\n".join(selected_lines)
            )

        except FileNotFoundError:
            return FileChunk(
                file_path=file_path,
                start_line=0,
                end_line=0,
                content="",
                error=f"File not found: {file_path}"
            )
        except Exception as e:
            return FileChunk(
                file_path=file_path,
                start_line=0,
                end_line=0,
                content="",
                error=f"Error reading file: {e}"
            )
    
    @mcp.tool
    def read_dir(dir_path: str) -> DirEntriesOutput:
        """List directory entries relative to the project root (non-recursive)."""
        try:
            entries = os.listdir(safe_path_join(project_path, dir_path))
            return DirEntriesOutput(dir_path=dir_path, entries=entries)
        except Exception as e:
            return DirEntriesOutput(dir_path=dir_path, entries=[], error=f"Error reading directory: {e}")

    @mcp.tool(
        description="List directory entries relative to the project root. Max entries is 100.",
    )
    def tree_dir(dir_path: str, depth: int = 1) -> DirTreeOutput:
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
                 return DirTreeOutput(dir_path=dir_path, tree=[], error=f"Error: Directory not found at '{dir_path}'")
            results.append(dir_path)  # Add the root of the tree itself
            _walk(root_path, 1)
        except Exception as e:
            return DirTreeOutput(dir_path=dir_path, tree=[], error=f"Error processing directory '{dir_path}': {e}")

        return DirTreeOutput(dir_path=dir_path, tree=results[:max_entries])
    
    @mcp.tool
    def natural_language_search(query: str) -> SearchResultsOutput:
        """Search the repository using a natural-language query."""
        try:
            raw_results = seagoat.search(query)
            # Use pydantic's validation to coerce the raw dicts into the model.
            parsed_results = [SearchResult.model_validate(r) for r in raw_results]
            return SearchResultsOutput(results=parsed_results)
        except Exception as e:
            return SearchResultsOutput(results=[], error=str(e))
    
    return mcp
