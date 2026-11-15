"""v1.2.0 added folder-scoped Git settings (includeIf Profiles) and key usage locations."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_release_metadata_is_1_2_0():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.3.0"
    assert metadata.APP_VERSION_LABEL == "1.3.0"
    assert "filevers=(1, 3, 0, 0)" in (ROOT / "version_info.txt").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.3.0"


def test_1_2_modules_import_and_expose_api():
    from key_manager.git import profiles
    from key_manager.ssh import sshconfig
    from key_manager import usage
    from key_manager.web.api_beta3 import KeyManagerApi

    assert hasattr(profiles, "save_profile") and hasattr(profiles, "check_effective_config")
    assert hasattr(sshconfig, "parse_ssh_config")
    assert hasattr(usage, "collect_key_usage")
    for name in (
        "list_git_profiles",
        "save_git_profile",
        "delete_git_profile",
        "check_effective_git_config",
        "fix_profile_order",
        "get_key_usage",
        "open_backup_folder",
        "select_folder",
    ):
        assert callable(getattr(KeyManagerApi, name)), name


def test_frontend_has_profile_ui_and_usage_column():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    beta3 = (WEB / "beta3.js").read_text(encoding="utf-8")
    css = (WEB / "beta5.css").read_text(encoding="utf-8")
    server = (ROOT / "src" / "key_manager" / "web" / "server.py").read_text(encoding="utf-8")

    assert 'href="beta5.css"' in html
    # the web server serves static files from an allowlist; beta5.css must be on it
    assert '"/beta5.css"' in server
    assert 'id="profile-dialog"' in html
    assert 'id="profile-check-dialog"' in html
    assert 'id="profile-list"' in html
    assert 'id="dash-profiles"' in html
    assert html.count('scope="col">使用位置</th>') == 2  # SSH + GPG tables

    assert "list_git_profiles" in js and "get_key_usage" in js
    assert "usageCell" in js and "loadGitProfiles" in js
    assert "save_git_profile" in js and "fix_profile_order" in js
    assert "select_folder" in js  # mock + desktop picker fallback

    # Folder profiles use selection-only mode of the shared picker.
    assert "window.KmDirBrowser" in beta3
    assert "TbDirPicker.open" in beta3
    assert "options.pickOnly" in beta3
    assert "set_ssh_directory" in beta3

    assert ".profile-card" in css
    assert ".pf-folder-override" in css
    assert ".usage-chips" in css


def test_folder_picker_pick_only_does_not_change_ssh_directory():
    beta3 = (WEB / "beta3.js").read_text(encoding="utf-8")
    assert "if (options.pickOnly || !picked) return picked;" in beta3
    assert (beta3.index("if (options.pickOnly || !picked)")
            < beta3.index("set_ssh_directory"))


def test_docs_cover_profiles_and_worktree_limitation():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "資料夾 Git 設定（Profiles）" in readme
    assert "includeIf.gitdir/i:" in readme
    assert "worktree" in readme
    assert "## v1.2.0" in changelog
    assert changelog.index("## v1.2.0") < changelog.index("## v1.1.1")
