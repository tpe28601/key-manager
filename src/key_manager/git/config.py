from __future__ import annotations

from dataclasses import dataclass
import re

from key_manager.command import CommandResult, run_command
from key_manager.git.git_for_windows import FIXED_GIT_EXE, find_git_for_windows
from key_manager.gpg.git_gpg import FIXED_GIT_GPG, find_git_bundled_gpg


_FULL_FINGERPRINT = re.compile(r"^[A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?$")


@dataclass(frozen=True)
class GitGlobalConfig:
    name: str
    email: str
    signing_key: str
    commit_gpgsign: bool
    gpg_format: str
    gpg_program: str
    tag_gpgsign: bool = False


def _git_or_none():
    return find_git_for_windows()


def _read_value(key: str) -> str:
    git = _git_or_none()
    if git is None:
        return ""
    result = run_command([str(git), "config", "--global", "--get", key], timeout=15.0)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def read_global_git_config() -> GitGlobalConfig:
    if _git_or_none() is None:
        return GitGlobalConfig("", "", "", False, "", "", False)
    gpgsign = _read_value("commit.gpgsign").lower() in {"true", "yes", "on", "1"}
    tag_gpgsign = _read_value("tag.gpgSign").lower() in {"true", "yes", "on", "1"}
    return GitGlobalConfig(
        name=_read_value("user.name"),
        email=_read_value("user.email"),
        signing_key=_read_value("user.signingkey"),
        commit_gpgsign=gpgsign,
        gpg_format=_read_value("gpg.format"),
        gpg_program=_read_value("gpg.program"),
        tag_gpgsign=tag_gpgsign,
    )


def _require_success(result: CommandResult, action: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Git {action} failed")


def _require_git():
    git = _git_or_none()
    if git is None:
        raise RuntimeError(f"找不到 Git for Windows：{FIXED_GIT_EXE}")
    return git


def set_global_identity(name: str, email: str) -> None:
    name = " ".join(name.split())
    email = email.strip()
    if not name:
        raise ValueError("Git user.name is required")
    if not email or "@" not in email:
        raise ValueError("A valid Git user.email is required")
    git = _require_git()
    _require_success(run_command([str(git), "config", "--global", "user.name", name]), "user.name update")
    _require_success(run_command([str(git), "config", "--global", "user.email", email]), "user.email update")


def set_global_signing(fingerprint: str, enabled: bool) -> None:
    fingerprint = fingerprint.replace(" ", "").strip()
    if enabled and not _FULL_FINGERPRINT.fullmatch(fingerprint):
        raise ValueError("Enabling Git GPG signing requires a full GPG fingerprint")
    if fingerprint and not _FULL_FINGERPRINT.fullmatch(fingerprint):
        raise ValueError("GPG signing key must be a full fingerprint")

    git = _require_git()
    if enabled:
        if find_git_bundled_gpg() is None:
            raise RuntimeError(f"找不到固定的 Git GPG：{FIXED_GIT_GPG}")
        gpg = find_git_bundled_gpg()
        if gpg is None:
            raise RuntimeError(f"找不到固定的 Git GPG：{FIXED_GIT_GPG}")
        _require_success(
            run_command([str(git), "config", "--global", "gpg.program", str(gpg)]),
            "gpg.program update",
        )
        _require_success(
            run_command([str(git), "config", "--global", "gpg.format", "openpgp"]),
            "gpg.format update",
        )
    if fingerprint:
        _require_success(
            run_command([str(git), "config", "--global", "user.signingkey", fingerprint]),
            "signing key update",
        )
    value = "true" if enabled else "false"
    _require_success(
        run_command([str(git), "config", "--global", "commit.gpgsign", value]),
        "commit signing update",
    )
    _require_success(
        run_command([str(git), "config", "--global", "tag.gpgSign", value]),
        "tag signing update",
    )
