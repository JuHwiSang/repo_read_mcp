import os
import stat
import time
import gc
from typing import Any

import pygit2

__all__ = ["remove_readonly", "create_git_repo"]


def remove_readonly(func: Any, path: str, excinfo: Any) -> None:  # noqa: ANN401
    """Helper for shutil.rmtree to clear read-only bits on Windows.

    Mirrors the logic previously duplicated across multiple test files.
    """
    try:
        os.chmod(path, stat.S_IWUSR)
    except OSError:
        pass
    func(path)



def create_git_repo(test_dir: str) -> None:
    """Initialise a minimal git repository with two Python files.

    This helper factors out duplicated logic from test suites that need a
    throw-away repo containing `sample.py` and `another.py`.
    """
    repo = pygit2.init_repository(test_dir)

    # sample.py
    with open(os.path.join(test_dir, "sample.py"), "w", encoding="utf-8") as f:
        f.write("def hello_world():\n")
        f.write("    \"\"\"This is a sample function to greet the world.\"\"\"\n")
        f.write("    print(\"Hello, World!\")\n")

    # another.py
    with open(os.path.join(test_dir, "another.py"), "w", encoding="utf-8") as f:
        f.write("class Greeter:\n")
        f.write("    def greet(self, name=\"World\"):\n")
        f.write("        \"\"\"Greets a person by name.\"\"\"\n")
        f.write("        return f\"Hello, {name}!\"\n")

    index = repo.index
    index.add_all()
    index.write()

    now_utc = int(time.time())
    author = pygit2.Signature("Test Author", "test@example.com", now_utc - 86400, 0)
    committer = pygit2.Signature("Test Committer", "test@example.com", now_utc - 86400, 0)

    tree = index.write_tree()
    repo.create_commit("HEAD", author, committer, "Initial commit", tree, [])

    # Explicitly free libgit resources on some platforms (Windows)
    try:
        repo.free()
    except Exception:
        pass
    repo = None  # noqa: PLW2901 – ensure deref
    gc.collect()
