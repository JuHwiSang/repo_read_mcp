import argparse
import os
import sys

try:
    from repo_read_mcp.mcp import make_mcp_server
except ImportError:
    print("Error: repo_read_mcp package not found. If you executed this script directly, please use `python -m scripts.mcp_server` on project root directory.")
    sys.exit(1)

def main():
    """MCP 서버를 시작합니다."""
    parser = argparse.ArgumentParser(
        description="Run the MCP server for reading a repository."
    )
    parser.add_argument("repo_path", help="The path to the repository to be read.")
    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        print(f"Error: The provided path '{args.repo_path}' is not a valid directory.")
        sys.exit(1)

    repo_path = os.path.abspath(args.repo_path)
    repo_name = os.path.basename(repo_path)
    mcp_server = make_mcp_server(
        name=f"repo-read-{repo_name}", project_path=repo_path
    )

    print(f"Starting MCP server for '{repo_name}' on http://localhost:3000/mcp/")
    mcp_server.run(transport="http")


if __name__ == "__main__":
    main()
