import os

from .lib.utils import safe_path_join
from .seagoat import Seagoat
from .models import (
    FileChunk,
    ReadFilesOutput,
    DirEntriesOutput,
    ReadDirsOutput,
    DirTreeOutput,
    SearchResult,
    SearchResultsOutput,
)


class Repository:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.seagoat = Seagoat(project_path)
        self.seagoat.run()

    def read_files(self, file_paths: list[str]) -> ReadFilesOutput:
        results: list[FileChunk] = []
        for file_path in file_paths:
            try:
                abs_path = safe_path_join(self.project_path, file_path)
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                results.append(
                    FileChunk(
                        file_path=file_path,
                        start_line=1,
                        end_line=len(lines),
                        content="".join(lines),
                    )
                )

            except FileNotFoundError:
                results.append(
                    FileChunk(
                        file_path=file_path,
                        start_line=0,
                        end_line=0,
                        content="",
                        error=f"File not found: {file_path}",
                    )
                )
            except Exception as e:
                results.append(
                    FileChunk(
                        file_path=file_path,
                        start_line=0,
                        end_line=0,
                        content="",
                        error=f"Error reading file: {e}",
                    )
                )

        return ReadFilesOutput(files=results)

    def read_file_lines(
        self, file_path: str, start_line: int, end_line: int
    ) -> FileChunk:
        try:
            abs_path = safe_path_join(self.project_path, file_path)
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Adjust line numbers to be within bounds
            start = max(1, min(start_line, len(lines)))
            end = max(start, min(end_line, len(lines)))

            selected_lines = lines[start - 1 : end]

            return FileChunk(
                file_path=file_path,
                start_line=start,
                end_line=end,
                content="".join(selected_lines),
            )

        except FileNotFoundError:
            return FileChunk(
                file_path=file_path,
                start_line=0,
                end_line=0,
                content="",
                error=f"File not found: {file_path}",
            )
        except Exception as e:
            return FileChunk(
                file_path=file_path,
                start_line=0,
                end_line=0,
                content="",
                error=f"Error reading file: {e}",
            )

    def read_dirs(self, dir_paths: list[str]) -> ReadDirsOutput:
        results: list[DirEntriesOutput] = []
        for dir_path in dir_paths:
            try:
                entries = os.listdir(safe_path_join(self.project_path, dir_path))
                results.append(DirEntriesOutput(dir_path=dir_path, entries=entries))
            except Exception as e:
                results.append(
                    DirEntriesOutput(
                        dir_path=dir_path,
                        entries=[],
                        error=f"Error reading directory: {e}",
                    )
                )

        return ReadDirsOutput(dirs=results)

    def tree_dir(self, dir_path: str, depth: int = 1) -> DirTreeOutput:
        results = []
        root_path = safe_path_join(self.project_path, dir_path)

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
                return DirTreeOutput(
                    dir_path=dir_path,
                    tree=[],
                    error=f"Error: Directory not found at '{dir_path}'",
                )
            results.append(dir_path)  # Add the root of the tree itself
            _walk(root_path, 1)
        except Exception as e:
            return DirTreeOutput(
                dir_path=dir_path,
                tree=[],
                error=f"Error processing directory '{dir_path}': {e}",
            )

        return DirTreeOutput(dir_path=dir_path, tree=results[:max_entries])

    def search(self, query: str) -> SearchResultsOutput:
        try:
            raw_results = self.seagoat.search(query)
            # Use pydantic's validation to coerce the raw dicts into the model.
            parsed_results = [SearchResult.model_validate(r) for r in raw_results]
            return SearchResultsOutput(results=parsed_results)
        except Exception as e:
            return SearchResultsOutput(results=[], error=str(e))
