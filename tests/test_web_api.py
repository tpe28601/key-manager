from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


class DummyWindow:
    def create_file_dialog(self, *args, **kwargs):
        return None


def test_app_info_has_release_identity():
    from key_manager.web.api import KeyManagerApi

    api = KeyManagerApi(window_getter=lambda: DummyWindow())
    info = api.get_app_info()

    assert info["name"] == "Key Manager"
    assert info["version"] == "1.2.3"
    assert info["author"] == "Mike Lin"
    assert info["ui"] == "pywebview"


def test_list_ssh_keys_serializes_backend_models(monkeypatch, tmp_path: Path):
    from key_manager.ssh.models import SSHKeyInfo
    from key_manager.web import api as api_module

    key = SSHKeyInfo(
        name="id_ed25519",
        public_path=tmp_path / "id_ed25519.pub",
        private_path=tmp_path / "id_ed25519",
        algorithm="ssh-ed25519",
        fingerprint="SHA256:abc",
        comment="mike@example.com",
        has_private_key=True,
    )
    monkeypatch.setattr(api_module, "discover_ssh_keys", lambda _: [key])
    monkeypatch.setattr(
        api_module,
        "detect_platform",
        lambda: type("Info", (), {"ssh_dir": tmp_path, "system": "Windows", "home": tmp_path, "is_wsl": False})(),
    )
    monkeypatch.setattr(
        api_module,
        "get_agent_status",
        lambda: type("Status", (), {"available": True, "fingerprints": frozenset({"SHA256:abc"}), "message": ""})(),
    )

    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).list_ssh_keys()

    assert result == {
        "ok": True,
        "agent_status": "已載入 1 組 Key",
        "agent_available": True,
        "keys": [
            {
                "name": "id_ed25519",
                "public_path": str(tmp_path / "id_ed25519.pub"),
                "private_path": str(tmp_path / "id_ed25519"),
                "algorithm": "ssh-ed25519",
                "fingerprint": "SHA256:abc",
                "comment": "mike@example.com",
                "has_private_key": True,
                "agent_loaded": True,
            }
        ],
    }


def test_list_gpg_keys_serializes_dates(monkeypatch):
    from key_manager.gpg.models import GPGKeyInfo
    from key_manager.web import api as api_module

    key = GPGKeyInfo(
        fingerprint="A" * 40,
        user_id="Mike Lin <mike@example.com>",
        name="Mike Lin",
        email="mike@example.com",
        algorithm="ed25519",
        created_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
        expires_at=datetime(2028, 9, 14, tzinfo=timezone.utc),
        has_secret_key=True,
    )
    monkeypatch.setattr(api_module, "discover_gpg_keys", lambda: [key])

    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).list_gpg_keys()

    assert result["ok"] is True
    assert result["keys"][0]["fingerprint"] == "A" * 40
    assert result["keys"][0]["created_at"] == "2026-09-14T00:00:00+00:00"
    assert result["keys"][0]["expires_at"] == "2028-09-14T00:00:00+00:00"


def test_api_errors_are_returned_as_structured_messages(monkeypatch):
    from key_manager.web import api as api_module

    monkeypatch.setattr(api_module, "discover_gpg_keys", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).list_gpg_keys()

    assert result == {"ok": False, "error": "boom", "keys": []}


def test_create_ssh_key_never_echoes_passphrase(monkeypatch, tmp_path: Path):
    from key_manager.web import api as api_module

    captured = {}
    monkeypatch.setattr(
        api_module,
        "detect_platform",
        lambda: type("Info", (), {"ssh_dir": tmp_path, "system": "Windows", "home": tmp_path, "is_wsl": False})(),
    )

    def fake_generate(directory, filename, algorithm, comment, passphrase):
        captured.update(
            directory=directory,
            filename=filename,
            algorithm=algorithm,
            comment=comment,
            passphrase=passphrase,
        )
        return directory / filename, directory / f"{filename}.pub"

    monkeypatch.setattr(api_module, "generate_ssh_key", fake_generate)
    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).create_ssh_key(
        {
            "filename": "work_key",
            "algorithm": "ed25519",
            "comment": "mike@example.com",
            "passphrase": "super-secret",
        }
    )

    assert captured["passphrase"] == "super-secret"
    assert "super-secret" not in repr(result)
    assert result["ok"] is True


def test_read_git_config_is_json_safe(monkeypatch):
    from key_manager.git.config import GitGlobalConfig
    from key_manager.web import api as api_module

    monkeypatch.setattr(
        api_module,
        "read_global_git_config",
        lambda: GitGlobalConfig(
            name="Mike Lin",
            email="mike@example.com",
            signing_key="B" * 40,
            commit_gpgsign=True,
            gpg_format="openpgp",
            gpg_program=r"C:\\Program Files\\Git\\usr\\bin\\gpg.exe",
            tag_gpgsign=True,
        ),
    )
    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).read_git_config()

    assert result["ok"] is True
    assert result["config"]["name"] == "Mike Lin"
    assert result["config"]["commit_gpgsign"] is True
    assert result["config"]["tag_gpgsign"] is True


def test_create_gpg_key_delegates_passphrase_to_native_pinentry(monkeypatch):
    from key_manager.command import CommandResult
    from key_manager.web import api as api_module

    captured = {}

    def fake_create(name, email, expire, algorithm):
        captured.update(name=name, email=email, expire=expire, algorithm=algorithm)
        return CommandResult(0, "", "")

    monkeypatch.setattr(api_module, "create_gpg_key", fake_create)
    result = api_module.KeyManagerApi(window_getter=lambda: DummyWindow()).create_gpg_key(
        {
            "name": "Mike",
            "email": "mike@example.com",
            "expire": "2y",
            "algorithm": "ed25519",
            # Old clients may still send this; backend must not forward it.
            "passphrase": "must-not-be-forwarded",
        }
    )

    assert result["ok"] is True
    assert captured == {
        "name": "Mike",
        "email": "mike@example.com",
        "expire": "2y",
        "algorithm": "ed25519",
    }
