"""v1.2.1 split folder settings (Profiles) into its own nav page and fixed the
directory picker painting behind modal dialogs (native dialog top layer)."""

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_release_metadata_is_current():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.2.4"
    assert metadata.APP_VERSION_LABEL == "1.2.4"
    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.4"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v1.2.2" in changelog
    assert changelog.index("## v1.2.2") < changelog.index("## v1.2.1")


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

    # A modal <dialog> paints in the top layer AND makes everything outside it
    # inert, so the picker must be re-parented INTO the dialog (same trick as
    # the toast host) — hiding the dialog instead leaves it unclickable.
    reattach = re.search(
        r"dialog\[open\][\s\S]*?const request = TbDirPicker\.open\([\s\S]*?"
        r"const pickerRoot = document\.querySelector\('\.tb-dp'\)[\s\S]*?"
        r"hostDialog\.append\(pickerRoot\)[\s\S]*?"
        r"picked = await request[\s\S]*?\} finally \{[\s\S]*?"
        r"removeEventListener\('cancel', guardCancel\)",
        beta3)
    assert reattach, "openDirBrowser must re-parent .tb-dp into the open dialog and keep the Esc-cancel guard"
    # the old hide-the-dialog approach must be gone (dialog would keep inert-ing the picker)
    assert "d.style.display = 'none'" not in beta3
    notify_at = beta3.index("if (pickerError) return notify")
    assert reattach.end() < notify_at, "the error toast must fire after the picker settles"
