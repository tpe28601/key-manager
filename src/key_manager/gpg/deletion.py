from __future__ import annotations

import re

from key_manager.command import CommandResult, run_command
from .git_gpg import FIXED_GIT_BASH, find_git_bash
from .runtime import run_git_gpg


_FINGERPRINT = re.compile(r"^[A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?$")


def _validate_fingerprint(fingerprint: str) -> str:
    value = fingerprint.replace(" ", "").strip()
    if not _FINGERPRINT.fullmatch(value):
        raise ValueError("A full 40- or 64-hex-character GPG fingerprint is required")
    return value


def delete_gpg_key(fingerprint: str) -> CommandResult:
    """Delete both secret and public parts of one GPG key by full fingerprint."""
    fingerprint = _validate_fingerprint(fingerprint)
    if find_git_bash() is None:
        return CommandResult(127, "", f"找不到 Git Bash：{FIXED_GIT_BASH}")
    return run_git_gpg(
        ["--batch", "--yes", "--delete-secret-and-public-key", fingerprint],
        runner=run_command,
        timeout=120.0,
    )
