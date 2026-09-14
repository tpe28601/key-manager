from __future__ import annotations

from pathlib import Path
import re

from key_manager.command import run_command
from .git_gpg import FIXED_GIT_BASH, find_git_bash
from .runtime import run_git_gpg


_FINGERPRINT = re.compile(r"^[A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?$")


def _validate_fingerprint(fingerprint: str) -> str:
    value = fingerprint.replace(" ", "").strip()
    if not _FINGERPRINT.fullmatch(value):
        raise ValueError("A full 40- or 64-hex-character GPG fingerprint is required")
    return value


def armor_public_key(fingerprint: str) -> str:
    fingerprint = _validate_fingerprint(fingerprint)
    if find_git_bash() is None:
        raise RuntimeError(f"找不到 Git Bash：{FIXED_GIT_BASH}")
    result = run_git_gpg(["--batch", "--armor", "--export", fingerprint], runner=run_command, timeout=60.0)
    if result.returncode != 0 or "BEGIN PGP PUBLIC KEY BLOCK" not in result.stdout:
        raise RuntimeError(result.stderr.strip() or "GPG public key export failed")
    return result.stdout


def export_gpg_public_key(fingerprint: str, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(str(destination))
    armored = armor_public_key(fingerprint)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        output.write(armored)
