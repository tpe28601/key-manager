from __future__ import annotations

from pathlib import Path
import os


FIXED_GIT_EXE = r"C:\Program Files\Git\cmd\git.exe"
FIXED_GIT_SSH = r"C:\Program Files\Git\usr\bin\ssh.exe"
FIXED_GIT_SSH_ADD = r"C:\Program Files\Git\usr\bin\ssh-add.exe"
FIXED_GIT_SSH_AGENT = r"C:\Program Files\Git\usr\bin\ssh-agent.exe"
FIXED_GIT_SSH_KEYGEN = r"C:\Program Files\Git\usr\bin\ssh-keygen.exe"
FIXED_GIT_SSH_ASKPASS_CANDIDATES = (
    r"C:\Program Files\Git\mingw64\libexec\git-core\git-gui--askpass.exe",
    r"C:\Program Files\Git\mingw64\libexec\git-core\git-askpass.exe",
)


def _is_windows() -> bool:
    return os.name == "nt"


def _existing(path: str) -> Path | None:
    if not _is_windows():
        return None
    candidate = Path(path)
    return candidate if candidate.is_file() else None


def find_git_for_windows() -> Path | None:
    return _existing(FIXED_GIT_EXE)


def find_git_ssh() -> Path | None:
    return _existing(FIXED_GIT_SSH)


def find_git_ssh_add() -> Path | None:
    return _existing(FIXED_GIT_SSH_ADD)


def find_git_ssh_agent() -> Path | None:
    return _existing(FIXED_GIT_SSH_AGENT)


def find_git_ssh_keygen() -> Path | None:
    return _existing(FIXED_GIT_SSH_KEYGEN)


def find_git_ssh_askpass() -> Path | None:
    for path in FIXED_GIT_SSH_ASKPASS_CANDIDATES:
        candidate = _existing(path)
        if candidate is not None:
            return candidate
    return None
