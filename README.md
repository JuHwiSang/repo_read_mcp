# repo-read-mcp

> **Warning**
> This is a personal project and is currently in a **highly unstable** state. Use with caution.

`repo-read-mcp` provides read-only tools for a given repository as an fastMCP server.

## Key Features

This server provides the following tools for interacting with repository source code:

*   **`read_files`**: Reads the entire content of one or more files.
*   **`read_file_lines`**: Reads the content of a specified line range within a specific file.
*   **`read_dirs`**: Lists entries within one or more directories (non-recursive).
*   **`tree_dir`**: Recursively lists directory entries up to a specified depth.
*   **`search`**: Performs a semantic search on the repository using a natural language query. Regular expressions are also supported.

## How it Works

Internally, `repo-read-mcp` builds a Docker container image that includes the `Seagoat` search engine and the target repository's source code. This container is then launched in the background.

This approach is chosen because Seagoat has a complex set of runtime dependencies—large embedding models, specialized Python libraries, and system packages—that make it difficult to run reliably in a non-containerized environment.

When the MCP server receives a request for a semantic search, it sends a command to the running container. The container executes the natural language search and returns the results.

For standard read operations like `read_files`, `read_dirs`, etc., the server interacts directly with the repository path on the host filesystem, not through the container.

The Docker container is automatically stopped and removed when the main program exits.

## Requirements

*   **Docker**: Required for the semantic search feature (`seagoat`).
*   **Python**: `>=3.13`

## Installation

Install the necessary packages via `pip` to use the project.

```bash
pip install .
```

## Usage

A formal CLI is not yet supported.

### As a Library (Recommended)

It is recommended to use the `make_mcp_server` function by importing it.

```python
from repo_read_mcp import make_mcp_server

# Path to the repository you want to analyze
repo_path = "/path/to/your/repository"

# Create an MCP server instance
mcp_server = make_mcp_server(name="my-repo-analyzer", project_path=repo_path)

# Integrate and use the created server in your application.
# Example: mcp_server.run(transport="http")
```

### Direct Execution

For development and testing purposes, you can run the server directly from the project root.

```bash
python -m scripts.mcp_server /path/to/your/repository
```

### Preparing the `Seagoat` Image in Advance

The semantic search feature uses `Seagoat` internally, which requires a Docker image. This image includes embedding models and can take time to build. By creating a `Seagoat` instance and calling its `.prepare()` method in advance, you can pre-build the image to avoid long delays on the first use of the search feature. This step is optional; if not performed, the image will be built automatically on the first use.

You can import and use the `Seagoat` class directly.

```python
from repo_read_mcp.seagoat import Seagoat

# Path to the repository you want to analyze
repo_path = "/path/to/your/repository"

# Create a Seagoat instance for your repository
seagoat = Seagoat(repo_path=repo_path)

# Build the Docker image required for seagoat. This will be cached for future runs.
seagoat.prepare()
```