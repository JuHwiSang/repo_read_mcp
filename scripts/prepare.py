import sys
import os
import argparse

try:
    from repo_read_mcp.seagoat import Seagoat
except ImportError:
    print("Error: repo_read_mcp package not found. If you executed this script directly, please use `python -m scripts.prepare` on project root directory.")
    sys.exit(1)


def main():
    """
    Builds the Seagoat Docker image for a specific repository without running it.
    """
    parser = argparse.ArgumentParser(
        description="Prepare the Seagoat Docker image for a repository."
    )
    parser.add_argument("repo_path", help="The path to the repository to be prepared.")
    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        print(f"Error: The provided path '{args.repo_path}' is not a valid directory.")
        sys.exit(1)
        
    try:
        print(f"Preparing Seagoat for repository: {args.repo_path}")
        seagoat_instance = Seagoat(repo_path=args.repo_path)
        seagoat_instance.prepare()
        print("\nPreparation complete. The Docker image is built and ready.")
    except Exception as e:
        print(f"\nAn unexpected error occurred during preparation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
