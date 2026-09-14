from __future__ import annotations

from key_manager.command import CommandResult, run_command
from .git_gpg import FIXED_GIT_BASH, find_git_bash
from .runtime import run_git_gpg


def create_gpg_key(
    name: str,
    email: str,
    expire: str = "2y",
    algorithm: str = "rsa4096",
) -> CommandResult:
    """Create a GPG key through Git Bash and let GnuPG/Pinentry own passphrases.

    Key Manager intentionally never accepts or forwards a GPG passphrase.
    GnuPG launches its configured Pinentry UI for passphrase setup.
    """
    name = " ".join(name.split())
    email = email.strip()
    if not name:
        raise ValueError("Name is required")
    if not email or "@" not in email:
        raise ValueError("A valid email address is required")
    if expire not in {"0", "1y", "2y", "3y", "5y"}:
        raise ValueError("Unsupported expiration value")
    if algorithm not in {"ed25519", "rsa4096"}:
        raise ValueError("Unsupported GPG key algorithm")
    if find_git_bash() is None:
        return CommandResult(127, "", f"找不到 Git Bash：{FIXED_GIT_BASH}")
    return run_git_gpg(
        [
            "--no-tty",
            "--pinentry-mode",
            "ask",
            "--quick-generate-key",
            f"{name} <{email}>",
            algorithm,
            "sign",
            expire,
        ],
        runner=run_command,
        timeout=300.0,
    )
