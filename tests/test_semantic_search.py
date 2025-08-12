import pytest
import os
import shutil
import tempfile
import pygit2
import time
from repo_read_mcp.seagoat import Seagoat

@pytest.fixture(scope="module")
def temp_repo():
    """Set up a temporary git repository for testing in a temp directory."""
    test_dir = tempfile.mkdtemp()
    
    # Initialize a git repository
    repo = pygit2.init_repository(test_dir)
    
    # Create a sample file
    with open(os.path.join(test_dir, "sample.py"), "w") as f:
        f.write("def hello_world():\n")
        f.write("    \"\"\"This is a sample function to greet the world.\"\"\"\n")
        f.write("    print(\"Hello, World!\")\n")

    # Create another sample file
    with open(os.path.join(test_dir, "another.py"), "w") as f:
        f.write("class Greeter:\n")
        f.write("    def greet(self, name=\"World\"):\n")
        f.write("        \"\"\"Greets a person by name.\"\"\"\n")
        f.write("        return f\"Hello, {name}!\"\n")

    # Add and commit the files
    index = repo.index
    index.add_all()
    index.write()
    
    now_utc = int(time.time())
    
    author = pygit2.Signature("Test Author", "test@example.com", now_utc - 86400, 0)
    committer = pygit2.Signature("Test Committer", "test@example.com", now_utc - 86400, 0)

    tree = index.write_tree()
    repo.create_commit("HEAD", author, committer, "Initial commit", tree, [])

    repo_path = os.path.abspath(test_dir)
    yield repo_path  # Provide the repo path to the tests
    
    # Teardown: clean up the temporary repository
    shutil.rmtree(test_dir)

@pytest.fixture(scope="module")
def searcher(temp_repo):
    """Initializes the Seagoat class once per module."""
    return Seagoat(repo_path=temp_repo)

def test_search_function_definition(searcher):
    """Test searching for a function definition."""
    query = "a function that greets"
    results = searcher.search(query)
    
    assert isinstance(results, list)
    assert len(results) > 0, "Should find at least one result"
    
    found_expected_file = False
    for result in results:
        if "another.py" in result['file']:
            assert "def greet" in result['code']
            assert result['start_line'] == 2
            assert result['end_line'] == 4
            found_expected_file = True
            break

    assert found_expected_file, "Did not find the expected function in search results."

# def test_search_docstring(searcher):
#     """Test searching based on a docstring."""
#     query = "sample function to say hi"
#     results = searcher.search(query)
    
#     assert isinstance(results, list)
#     assert len(results) > 0

#     found_expected_file = False
#     for result in results:
#         if "sample.py" in result['file']:
#              assert "def hello_world" in result['code']
#              assert result['start_line'] == 1
#              assert result['end_line'] == 3
#              found_expected_file = True
#              break
    
#     assert found_expected_file, "Did not find the expected docstring in search results."
