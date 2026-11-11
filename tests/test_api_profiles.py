"""API-level tests for the 1.2 folder-profile and key-usage methods.

Every call goes through KeyManagerApi directly (same object the web server
exposes) under the git_env sandbox, so the real ~/.gitconfig is untouched.
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from key_manager.git import profiles
from key_manager.git.git_for_windows import find_git_for_windows
from key_manager.web.api_beta3 import KeyManagerApi

pytestmark = pytest.mark.skipif(find_git_for_windows() is None, reason="Git for Windows is not installed")

FAKE_FP = "E" * 40


def make_api():
    return KeyManagerApi(window_getter=lambda: None)


def _payload(**overrides):
    base = {
        "name": "Client A",
        "note": "",
        "folders": ["D:/Work/ClientA/"],
        "fields": {"user.name": "Alice Chen", "user.email": "alice@client-a.example.com"},
    }
    base.update(overrides)
    return base


def test_list_git_profiles_success_and_error(git_env, monkeypatch):
    api = make_api()
    result = api.list_git_profiles()
    assert result["ok"] is True
    assert result["profiles"] == []
    assert str(result["global_path"]) in str(profiles.global_config_path())

    api.save_git_profile(_payload())
    listed = api.list_git_profiles()["profiles"]
    assert len(listed) == 1
    assert listed[0]["name"] == "Client A"

    def boom():
        raise RuntimeError("git exploded")

    monkeypatch.setattr(profiles, "list_profiles", boom)
    failed = api.list_git_profiles()
    assert failed["ok"] is False
    assert "git exploded" in failed["error"]
    assert failed["profiles"] == []


def test_save_git_profile_with_key_and_delete(git_env, git_cli):
    from key_manager import settings

    ssh_dir = git_env / "home" / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_client_a.pub").write_text("ssh-ed25519 AAAA a@example.com\n", encoding="utf-8")
    (ssh_dir / "id_client_a").write_text("fake\n", encoding="utf-8")
    settings.set_ssh_dir(ssh_dir)

    api = make_api()
    saved = api.save_git_profile(
        _payload(fields={"user.name": "Alice", "user.email": "a@example.com", "ssh_key": "id_client_a"})
    )
    assert saved["ok"] is True
    assert saved["profile"]["fields"]["core.sshCommand"] == profiles.build_ssh_command(ssh_dir / "id_client_a")
    assert "已儲存" in saved["message"]

    # Custom command passthrough.
    edited = api.save_git_profile(
        _payload(
            id=saved["profile"]["id"],
            fields={"user.name": "Alice", "user.email": "a@example.com", "ssh_command": "plink -ssh key"},
        )
    )
    assert edited["profile"]["fields"]["core.sshCommand"] == "plink -ssh key"

    # Unknown ssh_key name -> error.
    bad = api.save_git_profile(
        _payload(id=saved["profile"]["id"], fields={"user.name": "A", "user.email": "a@example.com", "ssh_key": "ghost"})
    )
    assert bad["ok"] is False
    assert "ghost" in bad["error"]

    # Validation errors from profiles.py surface as ok=False.
    bad = api.save_git_profile(_payload(name=""))
    assert bad["ok"] is False and "名稱" in bad["error"]

    removed = api.delete_git_profile(saved["profile"]["id"])
    assert removed["ok"] is True
    assert removed["removed"] == ["D:/Work/ClientA/"]
    assert api.list_git_profiles()["profiles"] == []


def test_save_git_profile_bool_fields(git_env):
    api = make_api()
    saved = api.save_git_profile(
        _payload(
            fields={
                "user.name": "Alice",
                "user.email": "a@example.com",
                "user.signingkey": FAKE_FP,
                "commit.gpgsign": True,
                "tag.gpgSign": False,
            }
        )
    )
    assert saved["ok"] is True
    fields = saved["profile"]["fields"]
    assert fields["commit.gpgsign"] == "true"
    assert fields["tag.gpgSign"] == "false"
    assert fields["user.signingkey"] == FAKE_FP


def test_delete_and_fix_unknown_id_errors(git_env):
    api = make_api()
    assert api.delete_git_profile("nope")["ok"] is False
    assert api.fix_profile_order("nope")["ok"] is False


def test_check_effective_git_config_roundtrip(git_env, git_cli):
    api = make_api()
    folder = git_env / "repo-in"
    folder.mkdir()
    api.save_git_profile(_payload(folders=[str(folder)]))
    git_cli("init", "-q", "-b", "main", str(folder))

    result = api.check_effective_git_config(str(folder))
    assert result["ok"] is True
    assert result["is_repo"] is True
    values = {row["key"]: row["value"] for row in result["rows"]}
    assert values["user.name"] == "Alice Chen"

    missing = api.check_effective_git_config(str(git_env / "no-such-folder"))
    assert missing["ok"] is False

    plain = git_env / "plain"
    plain.mkdir()
    not_repo = api.check_effective_git_config(str(plain))
    assert not_repo["ok"] is True and not_repo["is_repo"] is False


def test_fix_profile_order_via_api(git_env, git_cli):
    api = make_api()
    saved = api.save_git_profile(
        _payload(fields={"user.name": "Alice", "user.email": "a@example.com", "commit.gpgsign": "true"})
    )
    profile_id = saved["profile"]["id"]
    git_cli("config", "--global", "commit.gpgsign", "false")
    item = next(p for p in api.list_git_profiles()["profiles"] if p["id"] == profile_id)
    assert item["folders"][0]["overridden_keys"] == ["commit.gpgsign"]

    fixed = api.fix_profile_order(profile_id)
    assert fixed["ok"] is True
    assert "includeIf" in fixed["message"]
    item = next(p for p in api.list_git_profiles()["profiles"] if p["id"] == profile_id)
    assert item["folders"][0]["overridden_keys"] == []


def test_get_key_usage_via_api(git_env, git_cli, monkeypatch):
    from key_manager import settings
    from key_manager.gpg import discovery as gpg_discovery
    from key_manager.gpg.models import GPGKeyInfo
    from datetime import datetime, timezone

    ssh_dir = git_env / "home" / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_used.pub").write_text("ssh-ed25519 AAAA u@example.com\n", encoding="utf-8")
    (ssh_dir / "id_used").write_text("fake\n", encoding="utf-8")
    settings.set_ssh_dir(ssh_dir)

    monkeypatch.setattr(
        gpg_discovery,
        "discover_gpg_keys",
        lambda: [
            GPGKeyInfo(FAKE_FP, "A <a@example.com>", "A", "a@example.com", "ed25519",
                       datetime(2026, 1, 1, tzinfo=timezone.utc), None, True)
        ],
    )
    api = make_api()
    assert api.get_key_usage() == {"ok": True, "ssh": {}, "gpg": {}, "notes": []}

    api.save_git_profile(
        _payload(fields={"user.name": "Alice", "user.email": "a@example.com",
                         "ssh_key": "id_used", "user.signingkey": FAKE_FP})
    )
    usage = api.get_key_usage()
    assert usage["ok"] is True
    assert any(item["scope"] == "profile" for item in usage["ssh"]["id_used"])
    assert any(item["scope"] == "profile" for item in usage["gpg"][FAKE_FP])


def test_open_backup_folder_without_window(git_env):
    api = make_api()
    result = api.open_backup_folder()
    assert result["ok"] is True
    assert Path(result["path"]).name == "backups"
    assert Path(result["path"]).is_dir()


class FakeWindow:
    def __init__(self, selected):
        self.selected = selected

    def create_file_dialog(self, dialog_type, **kwargs):
        return self.selected


def test_select_folder(git_env, monkeypatch):
    from key_manager import settings

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(FileDialog=SimpleNamespace(FOLDER=20)))
    settings.set_ssh_dir(git_env / "home" / ".ssh")
    picking = KeyManagerApi(window_getter=lambda: FakeWindow(("D:/Picked",)))
    result = picking.select_folder()
    assert result["ok"] is True and result["path"] == "D:/Picked"

    cancelling = KeyManagerApi(window_getter=lambda: FakeWindow(None))
    result = cancelling.select_folder()
    assert result["ok"] is True and result["cancelled"] is True

    no_window = make_api().select_folder()
    assert no_window["ok"] is False and no_window["cancelled"] is True
