"""Utility to lock or unlock repository files for modification."""



from pathlib import Path

import os



ROOT = Path(__file__).resolve().parents[1]





def _iter_repo_files():

    """Yield all Python files within the repository."""

    for path in ROOT.rglob('*.py'):

        if '.git' in path.parts:

            continue

        yield path





def lock_repo():

    """Make repository Python files read-only."""

    for path in _iter_repo_files():

        path.chmod(0o444)





def unlock_repo():

    """Restore write permissions to repository Python files."""

    for path in _iter_repo_files():

        path.chmod(0o644)

