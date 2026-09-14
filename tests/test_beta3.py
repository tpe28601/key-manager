from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace


class FolderWindow:
    def __init__(self, selected: Path | None = None) -> None:
        self.selected = selected
        self.seen = None

    def create_file_dialog(self, dialog_type, **kwargs):
        self.seen = (dialog_type, kwargs)
        if self.selected is None:
            return None
        return (str(self.selected),)


def test_platform_uses_persistent_custom_ssh_directory(monkeypatch, tmp_path: Path):
    from key_manager import settings
    from key_manager.platform_info import detect_platform

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    custom = tmp_path / "CustomKeys"
    settings.set_ssh_dir(custom)

    assert detect_platform().ssh_dir == custom


def test_beta3_folder_picker_saves_selected_directory(monkeypatch, tmp_path: Path):
    from key_manager import settings
    from key_manager.web.api_beta3 import KeyManagerApi

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    current = tmp_path / "Current"
    selected = tmp_path / "Selected"
    settings.set_ssh_dir(current)
    window = FolderWindow(selected)
    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(FileDialog=SimpleNamespace(FOLDER=20)))

    result = KeyManagerApi(window_getter=lambda: window).select_ssh_directory()

    assert result == {"ok": True, "ssh_dir": str(selected)}
    assert settings.get_ssh_dir() == selected
    assert window.seen == (20, {"directory": str(current), "allow_multiple": False})


def test_beta3_folder_picker_cancel_keeps_current_directory(monkeypatch, tmp_path: Path):
    from key_manager import settings
    from key_manager.web.api_beta3 import KeyManagerApi

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    current = tmp_path / "Current"
    settings.set_ssh_dir(current)
    window = FolderWindow(None)
    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(FOLDER_DIALOG=30))

    result = KeyManagerApi(window_getter=lambda: window).select_ssh_directory()

    assert result == {"ok": True, "cancelled": True, "ssh_dir": str(current)}
    assert settings.get_ssh_dir() == current


def test_beta3_frontend_overrides_single_row_height_and_adds_path_controls():
    root = Path(__file__).resolve().parents[1]
    static = root / "src" / "key_manager" / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "beta3.css").read_text(encoding="utf-8")
    js = (static / "beta3.js").read_text(encoding="utf-8")

    assert 'href="beta3.css"' in html
    assert 'src="beta3.js"' in html
    assert ".table-wrap { min-height: 0 !important; }" in css
    assert "ssh-local-path" in js
    assert "select_ssh_directory" in js
    assert "reset_ssh_directory" in js


def test_launcher_uses_beta3_api_extension():
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "src" / "key_manager" / "web" / "launcher.py").read_text(encoding="utf-8")
    assert "from .api_beta3 import KeyManagerApi" in launcher
