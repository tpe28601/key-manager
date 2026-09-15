from pathlib import Path

from key_manager.command import CommandResult

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_theme_persists_in_key_manager_settings(monkeypatch, tmp_path: Path):
    from key_manager import settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    assert settings.get_theme() == "light"
    settings.set_theme("dark")
    assert settings.get_theme() == "dark"

    settings.set_theme("light")
    assert settings.get_theme() == "light"


def test_theme_rejects_unknown_value(monkeypatch, tmp_path: Path):
    from key_manager import settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    try:
        settings.set_theme("sepia")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown themes must be rejected")


def test_web_api_exposes_persistent_theme(monkeypatch, tmp_path: Path):
    from key_manager.web.api_beta3 import KeyManagerApi

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    api = KeyManagerApi(window_getter=lambda: None)

    assert api.get_theme() == {"ok": True, "theme": "light"}
    assert api.set_theme("dark") == {"ok": True, "theme": "dark"}
    assert api.get_theme() == {"ok": True, "theme": "dark"}


def test_frontend_uses_backend_theme_persistence():
    js = (WEB / "beta3.js").read_text(encoding="utf-8")

    assert "get_theme" in js
    assert "set_theme" in js
    assert "restoreTheme" in js
    assert "persistCurrentTheme" in js


def test_managed_agent_environment_persists(monkeypatch, tmp_path: Path):
    from key_manager import settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    env = {"SSH_AUTH_SOCK": "/tmp/agent.sock", "SSH_AGENT_PID": "4242"}

    settings.set_managed_agent_env(env)
    assert settings.get_managed_agent_env() == env

    settings.clear_managed_agent_env()
    assert settings.get_managed_agent_env() == {}


def test_agent_reconnects_to_persisted_managed_agent(monkeypatch, tmp_path: Path):
    from key_manager import settings
    from key_manager.ssh import agent as agent_module

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    settings.set_managed_agent_env({"SSH_AUTH_SOCK": "/tmp/agent.sock", "SSH_AGENT_PID": "4242"})
    monkeypatch.setattr(agent_module, "_managed_agent_env", {})
    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    monkeypatch.setattr(agent_module, "find_git_ssh_add", lambda: ssh_add)

    seen = {}

    def fake(args, timeout=30.0, env=None, input_text=None):
        seen["env"] = dict(env or {})
        return CommandResult(0, "4096 SHA256:abc test (RSA)\n", "")

    monkeypatch.setattr(agent_module, "run_command", fake)

    status = agent_module.get_agent_status()

    assert status.available is True
    assert "SHA256:abc" in status.fingerprints
    assert seen["env"]["SSH_AUTH_SOCK"] == "/tmp/agent.sock"
    assert seen["env"]["SSH_AGENT_PID"] == "4242"
    assert agent_module.is_managed_agent() is True


def test_release_build_uses_single_exe_without_upx():
    spec = (ROOT / "key_manager.spec").read_text(encoding="utf-8")
    build = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")

    assert "upx=False" in spec
    assert "exclude_binaries=True" not in spec
    assert "COLLECT(" not in spec
    assert "Key Manager 1.0.1" in build
    assert "single EXE without UPX" in build
    assert "Compress-Archive" not in build
    assert "Get-FileHash" in build
    assert "dist\\KeyManager.exe" in build


def test_release_metadata_is_1_0_1():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.0.1"
    assert metadata.APP_VERSION_LABEL == "1.0.1"
    assert 'version = "1.0.1"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "1.0.1" in version_info
