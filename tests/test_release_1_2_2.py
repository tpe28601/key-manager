"""v1.2.2 turned "open backup folder" into a real backup & restore dialog and
tightened the effective-value check dialog layout."""

from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "key_manager" / "web" / "static"


def test_release_metadata_is_current():
    from key_manager import metadata

    assert metadata.APP_VERSION == "1.2.2"
    assert metadata.APP_VERSION_LABEL == "1.2.2"
    assert "filevers=(1, 2, 2, 0)" in (ROOT / "version_info.txt").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.2"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v1.2.2" in changelog
    assert changelog.index("## v1.2.2") < changelog.index("## v1.2.1")


def test_api_exposes_backup_listing_preview_and_restore():
    from key_manager.web.api_beta3 import KeyManagerApi

    for name in ("list_config_backups", "read_config_backup", "restore_config_backup"):
        assert hasattr(KeyManagerApi, name), name


def test_backup_list_preview_and_restore_roundtrip(git_env):
    from key_manager.git import profiles

    global_path = profiles.global_config_path()
    original = global_path.read_text(encoding="utf-8")
    original_bytes = global_path.read_bytes()  # on-disk size (may be CRLF)

    profiles.backup_file(global_path)  # simulate the automatic pre-write backup
    global_path.write_text("[user]\n\tname = Broken Bot\n", encoding="utf-8")

    entries = profiles.list_backups()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["base"] == ".gitconfig"
    assert entry["target"] == "global"
    assert entry["restorable"] is True
    assert entry["path"] == str(global_path)
    assert entry["size"] == len(original_bytes)
    assert entry["modified"]

    preview = profiles.read_backup(entry["name"])
    assert preview["text"].replace("\r\n", "\n") == original  # raw bytes keep CRLF
    assert preview["truncated"] is False

    result = profiles.restore_backup(entry["name"])
    assert global_path.read_text(encoding="utf-8") == original
    assert result["target"] == str(global_path)
    assert result["kind"] == "global"

    # the restore backed up the pre-restore file too, so the action is rollback-able
    entries = profiles.list_backups()
    assert len(entries) == 2
    assert entries[0]["modified"] >= entries[1]["modified"]


def test_profile_backup_restore_with_display_name(git_env):
    from key_manager.git import profiles

    profile_file = profiles.profiles_dir() / "client-a.gitconfig"
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.write_text("[user]\n\tname = Client Alice\n", encoding="utf-8")
    profiles.profiles_json_path().write_text(
        json.dumps({"version": 1, "profiles": {"client-a": {"name": "Client A", "note": ""}}}),
        encoding="utf-8",
    )

    profiles.backup_file(profile_file)
    profile_file.write_text("[user]\n\tname = Oops\n", encoding="utf-8")

    entries = profiles.list_backups()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["target"] == "profile"
    assert entry["profile_id"] == "client-a"
    assert entry["profile_name"] == "Client A"
    assert entry["restorable"] is True

    result = profiles.restore_backup(entry["name"])
    assert result["kind"] == "profile"
    assert "Client Alice" in profile_file.read_text(encoding="utf-8")


def test_read_backup_truncates_large_files(git_env):
    from key_manager.git import profiles

    backups = profiles.backups_dir()
    backups.mkdir(parents=True, exist_ok=True)
    big = backups / ".gitconfig.20260101-010101"
    big.write_bytes(b"# " + b"x" * profiles._BACKUP_PREVIEW_LIMIT)
    preview = profiles.read_backup(big.name)
    assert preview["truncated"] is True
    assert len(preview["text"]) == profiles._BACKUP_PREVIEW_LIMIT


def test_restore_rejects_missing_foreign_and_traversal_names(git_env):
    from key_manager.git import profiles

    with pytest.raises(profiles.ProfileError):
        profiles.restore_backup("nope.gitconfig.20260101-010101")  # not in backups/
    with pytest.raises(profiles.ProfileError):
        profiles.restore_backup("../evil")  # path traversal
    with pytest.raises(profiles.ProfileError):
        profiles.read_backup("plain.txt")  # not a backup name

    # external includeIf targets (neither global nor in profiles/) are preview-only
    backups = profiles.backups_dir()
    backups.mkdir(parents=True, exist_ok=True)
    foreign = backups / "notes.gitconfig.20260101-010101"
    foreign.write_text("[user]\n", encoding="utf-8")
    entries = profiles.list_backups()
    assert entries[0]["target"] == "unknown"
    assert entries[0]["restorable"] is False
    with pytest.raises(profiles.ProfileError):
        profiles.restore_backup(foreign.name)


def test_backup_dialog_frontend_wiring():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    css = (WEB / "beta5.css").read_text(encoding="utf-8")

    assert "備份與還原…" in html  # toolbar button label
    assert 'id="backup-dialog"' in html
    assert 'id="backup-list"' in html
    assert 'id="backup-preview"' in html
    assert 'id="backup-restore"' in html
    assert 'id="backup-open-folder"' in html
    for hook in (
        "openBackupDialog",
        "loadBackups",
        "selectBackup",
        "restoreSelectedBackup",
        "list_config_backups",
        "read_config_backup",
        "restore_config_backup",
    ):
        assert hook in js, hook
    assert "$('#profile-backup-btn').addEventListener('click', openBackupDialog);" in js
    assert ".backup-item" in css
    assert "#backup-dialog" in css


def test_check_dialog_layout_fixes():
    css = (WEB / "beta5.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")

    # path + browse + run on one line; no empty table gap until results exist
    assert ".dir-pathbar { display: flex;" in css
    assert "#profile-check-dialog { width: min(620px" in css
    assert "#profile-check-dialog.has-result" in css
    assert "function resetCheckDialog()" in js
    assert "resetCheckDialog(); $('#profile-check-dialog').showModal();" in js
    assert "$('#profile-check-dialog').classList.add('has-result');" in js
