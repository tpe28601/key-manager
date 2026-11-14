from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_is_1_0_2():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.2.4"
    assert metadata.APP_VERSION_LABEL == "1.2.4"
    assert 'version = "1.2.4"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "1.2.4" in version_info
    build = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")
    assert "Key Manager 1.2.4" in build
