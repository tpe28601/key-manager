from pathlib import Path
import json


def test_custom_ssh_directory_persists_under_local_appdata(monkeypatch, tmp_path: Path):
    from key_manager import settings

    local_appdata = tmp_path / "LocalAppData"
    custom = tmp_path / "Keys" / "ssh"
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    settings.set_ssh_dir(custom)

    assert settings.get_ssh_dir() == custom
    saved = json.loads((local_appdata / "KeyManager" / "settings.json").read_text(encoding="utf-8"))
    assert saved["ssh_dir"] == str(custom)
    assert not custom.exists(), "Saving a path must not create the key directory"


def test_reset_ssh_directory_returns_to_user_ssh_default(monkeypatch, tmp_path: Path):
    from key_manager import settings

    local_appdata = tmp_path / "LocalAppData"
    custom = tmp_path / "Keys"
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setattr(settings, "_home_dir", lambda: tmp_path / "Home")

    settings.set_ssh_dir(custom)
    settings.reset_ssh_dir()

    assert settings.get_ssh_dir() == tmp_path / "Home" / ".ssh"
    saved = json.loads((local_appdata / "KeyManager" / "settings.json").read_text(encoding="utf-8"))
    assert "ssh_dir" not in saved


def test_invalid_settings_file_falls_back_to_default(monkeypatch, tmp_path: Path):
    from key_manager import settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setattr(settings, "_home_dir", lambda: tmp_path / "Home")
    path = settings.settings_path()
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")

    assert settings.get_ssh_dir() == tmp_path / "Home" / ".ssh"
