from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_frontend_has_four_primary_pages_and_no_emoji_icons():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'data-page="dashboard"' in html
    assert 'data-page="ssh"' in html
    assert 'data-page="gpg"' in html
    assert 'data-page="git"' in html
    assert "總覽" in html and "SSH 金鑰" in html and "GPG 金鑰" in html and "Git 設定" in html
    emoji_ranges = re.compile(r"[\U0001F300-\U0001FAFF]")
    assert not emoji_ranges.search(html)


def test_icons_are_vendored_iconify_tabler_svg():
    icons = (WEB / "icons.js").read_text(encoding="utf-8")
    assert "@iconify-json/tabler" in icons
    assert "tabler:layout-dashboard" in icons
    assert "tabler:key" in icons
    assert "tabler:shield-lock" in icons
    assert "tabler:brand-git" in icons
    assert 'viewBox="0 0 24 24"' in icons


def test_css_has_real_dark_theme_clear_selection_and_large_scrollbars():
    css = (WEB / "app.css").read_text(encoding="utf-8")
    assert '[data-theme="dark"]' in css
    assert "scrollbar-width" in css
    assert "::-webkit-scrollbar" in css
    assert "14px" in css
    assert ".key-row.selected" in css
    assert "--selection" in css


def test_frontend_has_mock_preview_fallback_for_browser_qa():
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "loadMockData" in js
    assert "pywebviewready" in js
    assert "window.pywebview.api" in js


def test_create_dialog_cancel_buttons_are_non_submitting_and_gpg_has_algorithm_selector():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="ssh-cancel" type="button"' in html
    assert 'id="gpg-cancel" type="button"' in html
    assert 'name="algorithm"' in html
    assert '<option value="rsa4096" selected>RSA 4096</option>' in html


def test_frontend_exposes_delete_actions_with_confirmation():
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "delete_ssh_key" in js
    assert "delete_gpg_key" in js
    assert "window.confirm" in js
    assert "tabler:trash" in js


def test_gpg_dialog_delegates_passphrase_to_native_pinentry():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    start = html.index('id="gpg-dialog"')
    end = html.index('</dialog>', start)
    gpg_dialog = html[start:end]

    assert 'name="passphrase"' not in gpg_dialog
    assert 'name="confirm"' not in gpg_dialog
    assert "Pinentry" in gpg_dialog
    start_js = js.index("async function submitGpg")
    end_js = js.index("function setTheme", start_js)
    submit_gpg = js[start_js:end_js]
    assert "passphrase" not in submit_gpg
