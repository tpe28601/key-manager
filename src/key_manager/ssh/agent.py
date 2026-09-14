from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile

from key_manager.command import CommandResult, run_command
from key_manager.git.git_for_windows import (
    FIXED_GIT_SSH_ADD,
    FIXED_GIT_SSH_AGENT,
    find_git_ssh_add,
    find_git_ssh_agent,
    find_git_ssh_askpass,
)


@dataclass(frozen=True)
class AgentStatus:
    available: bool
    fingerprints: frozenset[str]
    message: str


@dataclass(frozen=True)
class AgentIdentity:
    fingerprint: str
    comment: str
    algorithm: str
    public_key: str


# Environment of an agent started by this Key Manager process. Git for Windows'
# ssh-agent communicates through SSH_AUTH_SOCK, so every later ssh-add call must
# receive the exact environment printed by ssh-agent -s.
_managed_agent_env: dict[str, str] = {}


def format_agent_status(status: AgentStatus) -> str:
    """Return a user-facing SSH Agent state without implying network connectivity."""
    if status.available:
        count = len(status.fingerprints)
        if count:
            return f"已載入 {count} 組 Key"
        return "已啟動但未載入 Key"
    if "找不到 Git for Windows ssh-add" in status.message:
        return "Git SSH 工具不存在"
    return "未啟動"


def parse_agent_environment(text: str) -> dict[str, str]:
    """Parse the two variables emitted by `ssh-agent -s` without evaluating shell code."""
    sock = re.search(r"(?:^|\n)SSH_AUTH_SOCK=([^;\r\n]+);", text)
    pid = re.search(r"(?:^|\n)SSH_AGENT_PID=([0-9]+);", text)
    if not sock or not pid:
        return {}
    return {"SSH_AUTH_SOCK": sock.group(1), "SSH_AGENT_PID": pid.group(1)}


def fingerprint_public_key_line(public_key_line: str) -> str:
    """Return the OpenSSH SHA256 fingerprint for one public-key line."""
    parts = public_key_line.strip().split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError("Malformed SSH public key")
    blob_text = parts[1]
    padded = blob_text + "=" * (-len(blob_text) % 4)
    blob = base64.b64decode(padded, validate=True)
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{digest}"


def _managed_env() -> dict[str, str] | None:
    if not _managed_agent_env:
        return None
    env = dict(os.environ)
    env.update(_managed_agent_env)
    return env


def is_managed_agent() -> bool:
    return bool(_managed_agent_env)


def _run_ssh_add(
    args: list[str],
    *,
    timeout: float,
    extra_env: dict[str, str] | None = None,
) -> CommandResult:
    env = _managed_env()
    if extra_env:
        if env is None:
            env = dict(os.environ)
        env.update(extra_env)
    if env is None:
        return run_command(args, timeout=timeout)
    return run_command(args, timeout=timeout, env=env)


def _ssh_askpass_environment() -> dict[str, str]:
    askpass = find_git_ssh_askpass()
    if askpass is None:
        return {}
    helper = str(askpass)
    return {
        "SSH_ASKPASS": helper,
        "GIT_ASKPASS": helper,
        "SSH_ASKPASS_REQUIRE": "force",
        # Git for Windows' OpenSSH checks DISPLAY before using SSH_ASKPASS even
        # though git-gui--askpass.exe is a native Windows GUI helper.
        "DISPLAY": os.environ.get("DISPLAY") or "1",
    }


def get_agent_status() -> AgentStatus:
    ssh_add = find_git_ssh_add()
    if ssh_add is None:
        return AgentStatus(False, frozenset(), f"找不到 Git for Windows ssh-add：{FIXED_GIT_SSH_ADD}")
    result = _run_ssh_add([str(ssh_add), "-l"], timeout=10.0)
    text = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode == 0:
        fingerprints = frozenset(re.findall(r"SHA256:[^\s]+", result.stdout))
        return AgentStatus(True, fingerprints, text or "SSH Agent 可用")
    if result.returncode == 1 and "no identities" in text.lower():
        return AgentStatus(True, frozenset(), text or "SSH Agent 尚未加入金鑰")
    return AgentStatus(False, frozenset(), text or "SSH Agent 未啟動或不可用")


def list_agent_identities() -> list[AgentIdentity]:
    """List identities from the currently connected agent using public keys only."""
    ssh_add = find_git_ssh_add()
    if ssh_add is None:
        raise RuntimeError(f"找不到 Git for Windows ssh-add：{FIXED_GIT_SSH_ADD}")
    result = _run_ssh_add([str(ssh_add), "-L"], timeout=15.0)
    text = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode == 1 and "no identities" in text.lower():
        return []
    if result.returncode != 0:
        raise RuntimeError(text or "SSH Agent 無法列出 Key")

    identities: list[AgentIdentity] = []
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue
        try:
            fingerprint = fingerprint_public_key_line(line)
        except (ValueError, base64.binascii.Error):
            continue
        identities.append(
            AgentIdentity(
                fingerprint=fingerprint,
                comment=parts[2] if len(parts) == 3 else "",
                algorithm=parts[0],
                public_key=line,
            )
        )
    return identities


def start_managed_agent() -> CommandResult:
    global _managed_agent_env

    current = get_agent_status()
    if current.available:
        return CommandResult(0, current.message, "")

    ssh_agent = find_git_ssh_agent()
    if ssh_agent is None:
        return CommandResult(127, "", f"找不到 Git for Windows ssh-agent：{FIXED_GIT_SSH_AGENT}")
    result = run_command([str(ssh_agent), "-s"], timeout=15.0)
    if result.returncode != 0:
        return result
    parsed = parse_agent_environment("\n".join((result.stdout, result.stderr)))
    if not parsed:
        return CommandResult(1, result.stdout, result.stderr or "無法解析 ssh-agent 連線資訊")
    _managed_agent_env = parsed
    status = get_agent_status()
    if not status.available:
        return CommandResult(1, result.stdout, status.message)
    return result


def _start_managed_agent() -> CommandResult:
    """Compatibility wrapper for the Beta 3 internal helper."""
    return start_managed_agent()


def add_key_to_agent(private_path: Path) -> CommandResult:
    ssh_add = find_git_ssh_add()
    if ssh_add is None:
        return CommandResult(127, "", f"找不到 Git for Windows ssh-add：{FIXED_GIT_SSH_ADD}")

    status = get_agent_status()
    if not status.available:
        started = start_managed_agent()
        if started.returncode != 0:
            return started

    askpass_env = _ssh_askpass_environment()
    result = _run_ssh_add(
        [str(ssh_add), str(private_path)],
        timeout=120.0,
        extra_env=askpass_env or None,
    )
    if result.returncode != 0 and not askpass_env:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f"；原始錯誤：{detail}" if detail else ""
        return CommandResult(
            result.returncode,
            result.stdout,
            "找不到 Git for Windows SSH AskPass，無法為有 Passphrase 的 SSH Key 顯示密碼視窗" + suffix,
        )
    return result


def remove_agent_identity(fingerprint: str) -> CommandResult:
    """Remove one agent identity by fingerprint, including identities outside the local SSH folder."""
    fingerprint = fingerprint.strip()
    identity = next((item for item in list_agent_identities() if item.fingerprint == fingerprint), None)
    if identity is None:
        return CommandResult(1, "", f"SSH Agent 找不到 Key：{fingerprint}")

    ssh_add = find_git_ssh_add()
    if ssh_add is None:
        return CommandResult(127, "", f"找不到 Git for Windows ssh-add：{FIXED_GIT_SSH_ADD}")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".pub", encoding="utf-8", newline="\n", delete=False) as temp:
            temp.write(identity.public_key.rstrip("\r\n") + "\n")
            temp_path = Path(temp.name)
        return _run_ssh_add([str(ssh_add), "-d", str(temp_path)], timeout=30.0)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


def clear_agent_identities() -> CommandResult:
    ssh_add = find_git_ssh_add()
    if ssh_add is None:
        return CommandResult(127, "", f"找不到 Git for Windows ssh-add：{FIXED_GIT_SSH_ADD}")
    return _run_ssh_add([str(ssh_add), "-D"], timeout=30.0)


def stop_managed_agent() -> CommandResult:
    """Stop only an ssh-agent process that was launched by Key Manager."""
    global _managed_agent_env

    if not _managed_agent_env:
        return CommandResult(1, "", "目前 Agent 不是由 Key Manager 啟動，無法由此停止")
    ssh_agent = find_git_ssh_agent()
    if ssh_agent is None:
        return CommandResult(127, "", f"找不到 Git for Windows ssh-agent：{FIXED_GIT_SSH_AGENT}")

    env = _managed_env()
    result = run_command([str(ssh_agent), "-k"], timeout=15.0, env=env)
    if result.returncode == 0:
        _managed_agent_env = {}
    return result
