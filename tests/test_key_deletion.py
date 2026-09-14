from pathlib import Path

from key_manager.command import CommandResult


def test_delete_ssh_key_removes_private_and_public(monkeypatch, tmp_path: Path):
    from key_manager.ssh.models import SSHKeyInfo
    from key_manager.web import api as api_module

    private_path = tmp_path / "work_key"
    public_path = tmp_path / "work_key.pub"
    private_path.write_text("PRIVATE", encoding="utf-8")
    public_path.write_text("ssh-ed25519 AAAA comment\n", encoding="utf-8")
    key = SSHKeyInfo(
        name="work_key",
        public_path=public_path,
        private_path=private_path,
        algorithm="ssh-ed25519",
        fingerprint="SHA256:abc",
        comment="comment",
        has_private_key=True,
    )
    monkeypatch.setattr(
        api_module,
        "detect_platform",
        lambda: type("Info", (), {"ssh_dir": tmp_path, "system": "Windows", "home": tmp_path, "is_wsl": False})(),
    )
    monkeypatch.setattr(api_module, "discover_ssh_keys", lambda _: [key])

    result = api_module.KeyManagerApi(window_getter=lambda: None).delete_ssh_key("work_key")

    assert result["ok"] is True
    assert not private_path.exists()
    assert not public_path.exists()


def test_delete_gpg_key_uses_full_fingerprint_through_git_bash(monkeypatch):
    from key_manager.gpg.models import GPGKeyInfo
    from key_manager.web import api as api_module

    fingerprint = "A" * 40
    key = GPGKeyInfo(
        fingerprint=fingerprint,
        user_id="Mike Lin <mike@example.com>",
        name="Mike Lin",
        email="mike@example.com",
        algorithm="RSA",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        expires_at=None,
        has_secret_key=True,
    )
    monkeypatch.setattr(api_module, "discover_gpg_keys", lambda: [key])
    seen = {}

    def fake_delete(value):
        seen["fingerprint"] = value
        return CommandResult(0, "", "")

    monkeypatch.setattr(api_module, "delete_gpg_key", fake_delete)
    result = api_module.KeyManagerApi(window_getter=lambda: None).delete_gpg_key(fingerprint)

    assert result["ok"] is True
    assert seen["fingerprint"] == fingerprint


def test_delete_gpg_backend_uses_batch_full_fingerprint(monkeypatch):
    from key_manager.gpg import deletion

    fingerprint = "B" * 40
    seen = {}
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    monkeypatch.setattr(deletion, "find_git_bash", lambda: bash)
    monkeypatch.setattr("key_manager.gpg.runtime.find_git_bash", lambda: bash)

    def fake(args, timeout=30.0, env=None):
        seen["args"] = list(args)
        seen["timeout"] = timeout
        return CommandResult(0, "", "")

    monkeypatch.setattr(deletion, "run_command", fake)
    result = deletion.delete_gpg_key(fingerprint)

    assert result.returncode == 0
    assert seen["args"] == [
        str(bash), "-lc", 'exec gpg "$@"', "key-manager",
        "--batch", "--yes", "--delete-secret-and-public-key", fingerprint,
    ]
    assert seen["timeout"] == 120.0
