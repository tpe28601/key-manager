from pathlib import Path

from key_manager.command import CommandResult

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_release_metadata_is_current_1_0_series():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.2.3"
    assert metadata.APP_VERSION_LABEL == "1.2.3"

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in pyproject

    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "Beta" not in version_info
    assert "1.2.3" in version_info


def test_ssh_create_defaults_to_rsa4096_and_id_rsa(monkeypatch, tmp_path):
    from key_manager.web import api as api_module

    captured = {}
    monkeypatch.setattr(
        api_module,
        "detect_platform",
        lambda: type("Info", (), {"ssh_dir": tmp_path, "system": "Windows", "home": tmp_path, "is_wsl": False})(),
    )

    def fake_generate(directory, filename, algorithm, comment, passphrase):
        captured.update(filename=filename, algorithm=algorithm)
        return tmp_path / filename, tmp_path / f"{filename}.pub"

    monkeypatch.setattr(api_module, "generate_ssh_key", fake_generate)

    result = api_module.KeyManagerApi(window_getter=lambda: None).create_ssh_key({})

    assert result["ok"] is True
    assert captured == {"filename": "id_rsa", "algorithm": "rsa4096"}


def test_gpg_create_defaults_to_rsa4096(monkeypatch):
    from key_manager.gpg import generation

    seen = {}
    bash = Path(r"C:\\Program Files\\Git\\bin\\bash.exe")
    monkeypatch.setattr(generation, "find_git_bash", lambda: bash)
    monkeypatch.setattr("key_manager.gpg.runtime.find_git_bash", lambda: bash)

    def fake(args, timeout=30.0, env=None):
        seen["args"] = list(args)
        return CommandResult(0, "", "")

    monkeypatch.setattr(generation, "run_command", fake)
    generation.create_gpg_key("Mike", "mike@example.com")

    assert "rsa4096" in seen["args"]
    assert "ed25519" not in seen["args"]


def test_frontend_create_defaults_are_rsa4096():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'name="filename" value="id_rsa"' in html
    assert '<option value="rsa4096" selected>RSA 4096</option>' in html
    assert "預設使用 RSA 4096" in html
    assert "form.elements.filename.value = 'id_rsa'" in js


def test_readme_is_formal_product_documentation_without_beta_changelog():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# Key Manager")
    for heading in (
        "## 功能總覽",
        "## 系統需求",
        "## 安裝與執行",
        "## 建置 Windows EXE",
        "## 使用方法",
        "## 安全設計",
        "## 專案結構",
    ):
        assert heading in readme

    assert "Beta 6 修正" not in readme
    assert "Beta 5 修正" not in readme
    assert "Beta 4 新增" not in readme
    assert "Beta 3 修正" not in readme
    assert "PySide6" not in readme
