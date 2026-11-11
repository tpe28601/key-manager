"""Tests for the SSH/GPG key usage aggregation (SPEC-1.2 section 4.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from key_manager.git import profiles
from key_manager.git.git_for_windows import find_git_for_windows

pytestmark = pytest.mark.skipif(find_git_for_windows() is None, reason="Git for Windows is not installed")

FAKE_FP_A = "C" * 40
FAKE_FP_B = "D" * 40


@pytest.fixture()
def usage_env(git_env, git_cli, monkeypatch):
    from key_manager import settings

    ssh_dir = git_env / "home" / ".ssh"
    ssh_dir.mkdir()
    for name in ("id_global", "id_client_a", "id_web", "id_unused"):
        (ssh_dir / f"{name}.pub").write_text(f"ssh-ed25519 AAAA {name}@example.com\n", encoding="utf-8")
        (ssh_dir / name).write_text("fake private key\n", encoding="utf-8")
    settings.set_ssh_dir(ssh_dir)

    # Global core.sshCommand -> id_global
    git_cli("config", "--global", "core.sshCommand", profiles.build_ssh_command(ssh_dir / "id_global"))
    # A folder profile -> id_client_a
    profiles.save_profile({
        "name": "Client A",
        "folders": ["D:/Work/ClientA/"],
        "fields": {
            "user.name": "Alice Chen",
            "user.email": "alice@client-a.example.com",
            "core.sshCommand": profiles.build_ssh_command(ssh_dir / "id_client_a"),
            "user.signingkey": FAKE_FP_B,
        },
    })
    # ~/.ssh/config -> id_web (also via a differently-cased IdentityFile)
    (ssh_dir / "config").write_text(
        "Host team web\n"
        "    HostName web.example.com\n"
        "    IdentityFile ~/.ssh/id_web\n"
        "\n"
        "Host CASE\n"
        "    IdentityFile ~/.SSH/ID_WEB\n",
        encoding="utf-8",
    )

    from key_manager.gpg import discovery as gpg_discovery
    from key_manager.gpg.models import GPGKeyInfo
    from datetime import datetime, timezone

    fake_keys = [
        GPGKeyInfo(FAKE_FP_A, "Alice <a@example.com>", "Alice", "a@example.com", "ed25519",
                   datetime(2026, 1, 1, tzinfo=timezone.utc), None, True),
        GPGKeyInfo(FAKE_FP_B, "Bob <b@example.com>", "Bob", "b@example.com", "ed25519",
                   datetime(2026, 1, 1, tzinfo=timezone.utc), None, True),
    ]
    monkeypatch.setattr(gpg_discovery, "discover_gpg_keys", lambda: fake_keys)
    # Global user.signingkey as a 16-digit key id must match by suffix.
    git_cli("config", "--global", "user.signingkey", FAKE_FP_A[-16:])
    return ssh_dir


def test_collect_key_usage(usage_env):
    from key_manager.usage import collect_key_usage

    usage = collect_key_usage()
    ssh = usage["ssh"]

    assert any(item["scope"] == "global" for item in ssh.get("id_global", []))

    client_entries = ssh.get("id_client_a", [])
    assert any(
        item["scope"] == "profile"
        and item["label"] == "資料夾：D:/Work/ClientA/"
        and item["profile"] == "Client A"
        for item in client_entries
    )

    web_entries = ssh.get("id_web", [])
    assert any(item["scope"] == "ssh-host" and "SSH Host：web（web.example.com）" == item["label"] for item in web_entries)
    assert any(item["scope"] == "ssh-host" and item["label"] == "SSH Host：team（web.example.com）" for item in web_entries)
    # Case-insensitive IdentityFile match (CASE block, ~/.SSH/ID_WEB).
    assert any(item["scope"] == "ssh-host" and item["label"] == "SSH Host：CASE" for item in web_entries)

    assert "id_unused" not in ssh

    gpg = usage["gpg"]
    assert any(item["scope"] == "global" for item in gpg.get(FAKE_FP_A, []))
    assert any(
        item["scope"] == "profile" and item["label"] == "資料夾：D:/Work/ClientA/"
        for item in gpg.get(FAKE_FP_B, [])
    )
    assert usage["notes"] == []


def test_usage_notes_report_unresolved_includes(usage_env):
    (usage_env / "config").write_text(
        "Include ghost/*.conf\nHost x\n    IdentityFile ~/.ssh/id_unused\n", encoding="utf-8"
    )
    from key_manager.usage import collect_key_usage

    usage = collect_key_usage()
    assert any("Include" in note for note in usage["notes"])
