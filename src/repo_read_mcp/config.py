from importlib.resources import files


def get_dockerfile_template() -> bytes:
    """Return the base Dockerfile bytes from package data."""
    resource = files("repo_read_mcp.templates").joinpath("Dockerfile.seagoat.base")
    return resource.read_bytes()


def get_run_script_template() -> bytes:
    """Return the run.sh bytes from package data."""
    resource = files("repo_read_mcp.templates").joinpath("run.base.sh")
    return resource.read_bytes()


