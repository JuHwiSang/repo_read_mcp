from pydantic import BaseModel


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


class ReadDirsOutput(BaseModel):
    """Pydantic model representing multiple directory listings."""

    dirs: list[DirEntriesOutput]
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
