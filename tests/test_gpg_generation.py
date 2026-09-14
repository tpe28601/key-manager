from pathlib import Path

from key_manager.command import CommandResult
from key_manager.gpg.generation import create_gpg_key

BASH = Path(r"C:\\Program Files\\Git\\bin\\bash.exe")


def test_create_gpg_key_uses_native_pinentry_without_loopback(monkeypatch):
    seen = {}
    monkeypatch.setattr("key_manager.gpg.generation.find_git_bash", lambda: BASH)
    monkeypatch.setattr("key_manager.gpg.runtime.find_git_bash", lambda: BASH)

    def fake(args, timeout=30.0, env=None):
        seen["args"] = list(args)
        seen["timeout"] = timeout
        return CommandResult(0, "", "")

    monkeypatch.setattr("key_manager.gpg.generation.run_command", fake)
    create_gpg_key("Mike", "mike@example.com", "2y")

    assert seen["args"] == [
        str(BASH), "-lc", 'exec gpg "$@"', "key-manager",
        "--no-tty", "--pinentry-mode", "ask",
        "--quick-generate-key", "Mike <mike@example.com>", "rsa4096", "sign", "2y",
    ]
    flattened = " ".join(seen["args"]).lower()
    assert "--batch" not in flattened
    assert "--passphrase" not in flattened
    assert "loopback" not in flattened
    assert seen["timeout"] == 300.0


def test_create_gpg_key_supports_rsa4096_with_native_pinentry(monkeypatch):
    seen = {}
    monkeypatch.setattr("key_manager.gpg.generation.find_git_bash", lambda: BASH)
    monkeypatch.setattr("key_manager.gpg.runtime.find_git_bash", lambda: BASH)

    def fake(args, timeout=30.0, env=None):
        seen["args"] = list(args)
        return CommandResult(0, "", "")

    monkeypatch.setattr("key_manager.gpg.generation.run_command", fake)
    create_gpg_key("Mike", "mike@example.com", "2y", algorithm="rsa4096")

    assert "rsa4096" in seen["args"]
    assert "ed25519" not in seen["args"]
    assert "--no-tty" in seen["args"]
    mode_index = seen["args"].index("--pinentry-mode")
    assert seen["args"][mode_index + 1] == "ask"
    assert "--batch" not in seen["args"]
    assert "--passphrase-fd" not in seen["args"]
    assert "loopback" not in seen["args"]
