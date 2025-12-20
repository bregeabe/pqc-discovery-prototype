import os
import shutil
import subprocess
import uuid
from pathlib import Path

TEMP_ROOT = Path(__file__).resolve().parent / "tmp"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)

class RepoCloneError(Exception):
    """Custom error type for repo clone failures."""
    pass


def _validate_git_url(url: str):
    """
    Basic validation for URLs that support git clone.
    HTTPS recommended. SSH optional.
    """
    if not isinstance(url, str):
        raise ValueError("Repo URL must be a string")

    if url.startswith("http://") or url.startswith("https://") or url.startswith("git@"):
        return url

    raise ValueError(f"Unsupported repo URL format: {url}")


def _build_temp_path():
    """
    Returns a unique new directory path under TEMP_ROOT.
    """
    unique_id = uuid.uuid4().hex
    path = TEMP_ROOT / unique_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def clone_repo(repo_url: str) -> Path:
    """
    Clones a public repository into a fresh UUID temp dir and returns its path.

    Parameters:
        repo_url (str): URL for cloning (https://..., http://..., or git@...)

    Returns:
        Path: location of the cloned repo
    """
    repo_url = _validate_git_url(repo_url)
    working_dir = _build_temp_path()
    repo_path = working_dir / "repo"

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            text=True,
        )

        if result.returncode != 0:
            shutil.rmtree(working_dir, ignore_errors=True)
            raise RepoCloneError(f"Git clone failed: {result.stderr}")

        return repo_path

    except Exception as e:
        shutil.rmtree(working_dir, ignore_errors=True)
        raise RepoCloneError(str(e))


def remove_repo_path(path: Path):
    """
    Removes the cloned repo directory.
    """
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
