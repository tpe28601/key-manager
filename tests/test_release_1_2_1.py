"""v1.2.1 split folder settings (Profiles) into its own nav page and fixed the
directory picker painting behind modal dialogs (native dialog top layer)."""

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_release_metadata_is_current():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.2.1"
    assert metadata.APP_VERSION_LABEL == "1.2.1"
    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.1"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v1.2.1" in changelog
    assert changelog.index("## v1.2.1") < changelog.index("## v1.2.0")


def test_profiles_is_its_own_page():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'data-page="profiles"' in html
    assert 'id="page-profiles"' in html
    # the profiles panel moved out of the git page into its own section
    git_start = html.index('id="page-git"')
    profiles_start = html.index('id="page-profiles"')
    dialogs_start = html.index("<dialog")
    assert git_start < profiles_start < dialogs_start
    git_section = html[git_start:profiles_start]
    profiles_section = html[profiles_start:dialogs_start]
    assert len(git_section) > 100  # non-empty slice, order assumptions hold
    assert "git-profiles-panel" not in git_section
    assert "git-profiles-panel" in profiles_section
    assert 'id="profile-list"' in profiles_section


def test_dashboard_card_and_js_target_profiles_page():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'id="dash-profiles-card" data-action="open-profiles"' in html
    assert 'data-action="open-profiles"' in js
    assert "switchPage('profiles')" in js
    # the git page no longer loads the profiles list
    assert "if (state.page === 'git') await loadGit();" in js
    assert "if (state.page === 'profiles') await loadGitProfiles();" in js


def test_dir_picker_not_hidden_behind_modal_dialogs():
    beta3 = (WEB / "beta3.js").read_text(encoding="utf-8")

    # showModal() dialogs paint in the top layer; the picker must hide open
    # dialogs (with an Esc-cancel guard) while it runs and restore them
    # (also on error) before anything else touches them.
    hide = re.search(
        r"dialog\[open\][\s\S]*?d\.style\.display = 'none'[\s\S]*?"
        r"addEventListener\('cancel', guardCancel\)"
        r"[\s\S]*?try \{[\s\S]*?TbDirPicker\.open\([\s\S]*?"
        r"\} catch \(error\) \{[\s\S]*?\} finally \{[\s\S]*?"
        r"d\.style\.display = prevDisplay\[i\][\s\S]*?removeEventListener\('cancel', guardCancel\)",
        beta3)
    assert hide, "openDirBrowser must hide open dialogs around TbDirPicker.open and restore them in finally"
    notify_at = beta3.index("if (pickerError) return notify")
    assert hide.end() < notify_at, "the error toast must fire after the dialogs are restored"
