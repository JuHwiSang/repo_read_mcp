import pytest
import shutil
import tempfile

import docker
import docker.errors

from repo_read_mcp.seagoat import Seagoat

# Shared test helpers
from tests.helpers import create_git_repo, remove_readonly

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="module")
def temp_repo():
    """Set up a temporary git repository for testing in a temp directory."""
    test_dir = tempfile.mkdtemp()
    create_git_repo(test_dir)

    yield test_dir  # Provide the repo path to the tests

    # Teardown: clean up the temporary repository with proper error handling
    shutil.rmtree(test_dir, onexc=remove_readonly)

@pytest.fixture(scope="module")
def searcher(temp_repo):
    """Initializes the Seagoat class once per module."""
    s = Seagoat(repo_path=temp_repo)
    s.run()
    return s

async def test_prepare_builds_image_without_running(temp_repo):
    """Test that prepare() builds an image but does not run a container."""
    seagoat = Seagoat(repo_path=temp_repo)
    
    # Before prepare, image and container should be None
    assert seagoat.image is None
    assert seagoat.container is None
    
    seagoat.prepare()
    
    # After prepare, image should exist, but container should not
    assert seagoat.image is not None
    assert seagoat.tag, "Tag should be set after prepare"
    assert seagoat.container is None
    
    # Verify with the docker client that the image exists
    try:
        seagoat.docker_client.images.get(seagoat.tag)
    except docker.errors.ImageNotFound:
        pytest.fail(f"Image with tag {seagoat.tag} was not found after prepare()")


async def test_search_function_definition(searcher):
    """Test searching for a function definition."""
    query = "a function that greets"
    results = searcher.search(query)
    
    assert isinstance(results, list)
    assert len(results) > 0, "Should find at least one result"
    
    found_expected_file = False
    for result in results:
        if "another.py" in result['file']:
            assert "def greet" in result['code']
            assert result['start_line'] <= 2
            assert result['end_line'] <= 4
            found_expected_file = True
            break

    assert found_expected_file, "Did not find the expected function in search results."

async def test_search_docstring(searcher):
    """Test searching based on a docstring."""
    query = "sample function to say hi"
    results = searcher.search(query)
    
    assert isinstance(results, list)
    assert len(results) > 0

    found_expected_file = False
    for result in results:
        if "sample.py" in result['file']:
             assert "def hello_world" in result['code']
             assert result['start_line'] == 1
             assert result['end_line'] <= 3
             found_expected_file = True
             break
    
    assert found_expected_file, "Did not find the expected docstring in search results."
