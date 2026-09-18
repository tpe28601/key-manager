from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_uses_pywebview_not_qt():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"pywebview' in text.lower()
    assert "PySide6" not in text
    assert 'version = "1.0.2"' in text
    assert 'authors = [{name = "Mike Lin"}]' in text


def test_pyinstaller_spec_bundles_web_assets_and_windows_icon():
    text = (ROOT / "key_manager.spec").read_text(encoding="utf-8")
    assert "web/static" in text.replace("\\", "/")
    assert "key_manager.ico" in text
    assert "console=False" in text
    assert "upx=False" in text


def test_build_script_creates_single_exe_and_reports_size():
    text = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")
    assert "KeyManager.exe" in text
    assert "key_manager.spec" in text
    assert "pyinstaller" in text.lower()
    assert "Get-Item" in text
    assert "Get-FileHash" in text
    assert "Compress-Archive" not in text
