"""Where each SSH/GPG key is referenced (SPEC-1.2 section 4.5).

Combines the global Git config, folder profiles and ~/.ssh/config into a
usage map keyed by SSH key name and GPG fingerprint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from key_manager.git import profiles
from key_manager.settings import get_ssh_dir
from key_manager.ssh import sshconfig
from key_manager.ssh.discovery import discover_ssh_keys

_GLOBAL_LABEL = "全域"


def _host_label(pattern: str, hostname: str) -> str:
    if hostname:
        return f"SSH Host：{pattern}（{hostname}）"
    return f"SSH Host：{pattern}"


def _profile_folder_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for folder in profile.get("folders", []):
        label = folder.get("folder") or folder.get("condition", "")
        entries.append({
            "scope": "profile",
            "label": f"資料夾：{label}",
            "profile": profile.get("name", ""),
            "profile_id": profile.get("id", ""),
        })
    return entries


def _fingerprint_matches(value: str, fingerprint: str) -> bool:
    """Match full fingerprint, or a 16/8-digit key id by fingerprint suffix."""
    candidate = str(value).replace(" ", "").strip().upper()
    if candidate.startswith("0X"):
        candidate = candidate[2:]
    target = str(fingerprint).strip().upper()
    if not candidate or not target:
        return False
    if candidate == target:
        return True
    if len(candidate) in (8, 16) and candidate.isalnum() and target.endswith(candidate):
        return True
    return False


def collect_key_usage() -> dict[str, Any]:
    """Return {"ssh": {name: [entry]}, "gpg": {fingerprint: [entry]}, ...}."""
    ssh_usage: dict[str, list[dict[str, Any]]] = {}
    gpg_usage: dict[str, list[dict[str, Any]]] = {}
    notes: list[str] = []

    folder_profiles = [item for item in profiles.list_profiles() if item["kind"] != "unsupported"]

    # ---- SSH keys -------------------------------------------------------
    ssh_dir = get_ssh_dir()
    try:
        ssh_keys = discover_ssh_keys(ssh_dir)
    except OSError:
        ssh_keys = []
    by_path: dict[str, str] = {}
    for key in ssh_keys:
        if key.has_private_key:
            by_path[profiles.folder_key(str(key.private_path))] = key.name

    def ssh_hit(raw_path: str) -> str | None:
        if not raw_path:
            return None
        return by_path.get(profiles.folder_key(raw_path))

    def add_ssh(name: str, entry: dict[str, Any]) -> None:
        bucket = ssh_usage.setdefault(name, [])
        if entry not in bucket:
            bucket.append(entry)

    global_ssh = profiles.read_global_value("core.sshCommand")
    if global_ssh:
        name = ssh_hit(profiles.parse_ssh_command(global_ssh)["key_path"] or "")
        if name:
            add_ssh(name, {"scope": "global", "label": _GLOBAL_LABEL})

    for profile in folder_profiles:
        value = profile["fields"].get("core.sshCommand")
        if not value:
            continue
        name = ssh_hit(profiles.parse_ssh_command(value)["key_path"] or "")
        if name:
            for entry in _profile_folder_entries(profile):
                add_ssh(name, entry)

    ssh_config_path = ssh_dir / "config"
    config_data = sshconfig.parse_ssh_config(ssh_config_path)
    if config_data.unresolved_includes:
        notes.append("SSH config：有 Include 未解析（" + "、".join(config_data.unresolved_includes) + "）")
    if config_data.match_blocks:
        notes.append(f"SSH config：略過 {config_data.match_blocks} 個 Match 區塊")
    for block in config_data.hosts:
        for identity in block.identity_files:
            expanded = sshconfig.expand_identity_path(identity, ssh_dir)
            name = ssh_hit(expanded)
            if name:
                add_ssh(name, {
                    "scope": "ssh-host",
                    "label": _host_label(block.pattern, block.hostname),
                    "host": block.pattern,
                    "hostname": block.hostname,
                })

    # ---- GPG keys -------------------------------------------------------
    try:
        from key_manager.gpg.discovery import discover_gpg_keys

        gpg_keys = discover_gpg_keys()
    except Exception:
        gpg_keys = []

    def add_gpg(fingerprint: str, entry: dict[str, Any]) -> None:
        bucket = gpg_usage.setdefault(fingerprint, [])
        if entry not in bucket:
            bucket.append(entry)

    global_signing = profiles.read_global_value("user.signingkey")
    if global_signing:
        for key in gpg_keys:
            if _fingerprint_matches(global_signing, key.fingerprint):
                add_gpg(key.fingerprint, {"scope": "global", "label": _GLOBAL_LABEL})

    for profile in folder_profiles:
        value = profile["fields"].get("user.signingkey")
        if not value:
            continue
        for key in gpg_keys:
            if _fingerprint_matches(value, key.fingerprint):
                for entry in _profile_folder_entries(profile):
                    add_gpg(key.fingerprint, entry)

    return {"ssh": ssh_usage, "gpg": gpg_usage, "notes": notes}
