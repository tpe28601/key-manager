from __future__ import annotations

import os
from pathlib import Path


FIXED_GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"
FIXED_GIT_GPG = r"C:\Program Files\Git\usr\bin\gpg.exe"


def _is_windows() -> bool:
    return os.name == "nt"


def find_git_bash() -> Path | None:
    """Return the supported Git for Windows Bash executable."""
    if not _is_windows():
        return None
    candidate = Path(FIXED_GIT_BASH)
    return candidate if candidate.is_file() else None


def find_git_bundled_gpg() -> Path | None:
    """Return Git for Windows' bundled gpg.exe for Git configuration."""
    if not _is_windows():
        return None
    candidate = Path(FIXED_GIT_GPG)
    return candidate if candidate.is_file() else None


def git_bash_gpg_available() -> bool:
    return find_git_bash() is not None
