from __future__ import annotations

import os
from pathlib import Path
from typing import Union

__all__ = ["safe_path_join"]


def safe_path_join(base: Union[str, Path], *paths: Union[str, Path]) -> Path:
    """Join *paths to *base* ensuring the result stays within *base*.

    This helper is meant to mitigate simple ``..`` directory-traversal attacks
    when you need to join a user-supplied path to a known *base* directory.

    Parameters
    ----------
    base:
        The base directory that the result must remain inside of.
    *paths:
        One or more path components to join onto *base*.

    Returns
    -------
    pathlib.Path
        The resolved absolute path that is guaranteed to start with *base*.

    Raises
    ------
    ValueError
        If the resulting path escapes the *base* directory.

    Warning
    -------
    This function **does not** attempt to defend against symbolic-link based
    attack vectors. If an attacker controls a symlink that points outside the
    *base* directory, this check can be bypassed. If you must defend against
    symlink attacks, additional real-path checks or sandboxing is required.
    """

    # Convert to absolute, resolved Path objects (collapses "..", etc.).
    base_path = Path(base).resolve(strict=False)
    target_path = base_path.joinpath(*map(Path, paths)).resolve(strict=False)

    try:
        target_path.relative_to(base_path)
    except ValueError:
        # ``relative_to`` raises ValueError when *target_path* is not a subpath
        # of *base_path*.
        raise ValueError(f"Attempted path traversal outside base directory: {target_path}") from None

    return target_path
