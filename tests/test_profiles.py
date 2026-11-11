"""SPEC-1.2 backend tests for git/profiles.py.

The git_env fixture points GIT_CONFIG_GLOBAL and LOCALAPPDATA inside
tmp_path, so the real ~/.gitconfig and real user data are never touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from key_manager.git import profiles
from key_manager.git.git_for_windows import find_git_for_windows

pytestmark = pytest.mark.skipif(find_git_for_windows() is None, reason="Git for Windows is not installed")


def _fields(**overrides):
    base = {
        "user.name": "Alice Chen",
        "user.email": "alice@client-a.example.com",
    }
    base.update(overrides)
    return base


def test_normalize_folder():
    assert profiles.normalize_folder(r"D:\Work\ClientA") == "D:/Work/ClientA/"
    assert profiles.normalize_folder("D:/Work//ClientA/") == "D:/Work/ClientA/"
    assert profiles.normalize_folder("  D:/Work/ClientA/  ") == "D:/Work/ClientA/"
    with pytest.raises(Exception):
        profiles.normalize_folder("   ")


def test_global_config_path_prefers_env(git_env):
    assert profiles.global_config_path() == (git_env / "home" / ".gitconfig")


def test_create_update_delete_roundtrip_keeps_comments(git_env, git_cli):
    saved = profiles.save_profile({
        "name": "Client A",
        "folders": [r"D:\Work\ClientA"],
        "fields": _fields(),
    })
    assert saved["kind"] == "managed"
    assert saved["id"] == "client-a"
    assert saved["folders"][0]["folder"] == "D:/Work/ClientA/"
    assert saved["fields"]["user.name"] == "Alice Chen"
    assert saved["fields"]["user.email"] == "alice@client-a.example.com"
    assert saved["fields"]["user.signingkey"] is None  # inherit = key absent

    global_config = (git_env / "home" / ".gitconfig")
    text = global_config.read_text(encoding="utf-8")
    assert "# user comment: keep me" in text
    assert 'gitdir/i:D:/Work/ClientA/'.lower() in text.lower()

    profile_file = profiles.profiles_dir() / "client-a.gitconfig"
    assert profile_file.is_file()
    assert git_cli("config", "--file", str(profile_file), "--get", "user.name").stdout.strip() == "Alice Chen"

    # Update: change email, swap folder, enable commit signing.
    updated = profiles.save_profile({
        "id": "client-a",
        "name": "Client A",
        "folders": ["D:/Work/ClientA2"],
        "fields": _fields(**{"user.email": "alice2@client-a.example.com", "commit.gpgsign": "true"}),
    })
    assert updated["folders"][0]["folder"] == "D:/Work/ClientA2/"
    assert updated["fields"]["user.email"] == "alice2@client-a.example.com"
    assert updated["fields"]["commit.gpgsign"] == "true"
    assert updated["fields"]["user.name"] == "Alice Chen"  # untouched keys survive
    conditions = [item["condition"] for item in profiles.read_include_if()]
    assert conditions == ["gitdir/i:D:/Work/ClientA2/"]
    assert "# user comment: keep me" in global_config.read_text(encoding="utf-8")

    removed = profiles.delete_profile("client-a")
    assert removed == ["D:/Work/ClientA2/"]
    assert profiles.read_include_if() == []
    assert not profile_file.exists()
    # Managed profile file moves to backups instead of being deleted.
    backups = list(profiles.backups_dir().glob("client-a.gitconfig.*"))
    assert backups
    assert "# user comment: keep me" in global_config.read_text(encoding="utf-8")
    assert (profiles.profiles_json_path().read_text(encoding="utf-8").find("client-a")) == -1


def test_multiple_folders_one_profile_and_profiles_json(git_env):
    saved = profiles.save_profile({
        "name": "Client B",
        "note": "two folders",
        "folders": ["D:/Work/ClientB/repo1", r"E:\Work\ClientB"],
        "fields": _fields(**{"user.email": "bob@client-b.example.com"}),
    })
    assert sorted(f["folder"] for f in saved["folders"]) == ["D:/Work/ClientB/repo1/", "E:/Work/ClientB/"]
    import json

    meta = json.loads(profiles.profiles_json_path().read_text(encoding="utf-8"))
    assert meta["version"] == 1
    assert meta["profiles"]["client-b"] == {"name": "Client B", "note": "two folders"}


def test_same_folder_in_two_profiles_rejected(git_env):
    profiles.save_profile({"name": "P1", "folders": ["D:/Work/One"], "fields": _fields()})
    with pytest.raises(profiles.ProfileError, match="已被"):
        profiles.save_profile({"name": "P2", "folders": ["D:/Work/One/"], "fields": _fields()})
    # Same folder again on the same profile is fine (idempotent update).
    profiles.save_profile({"id": "p1", "name": "P1", "folders": ["D:/Work/One"], "fields": _fields()})


def test_nested_folders_warn_with_winner(git_env):
    profiles.save_profile({"name": "Outer", "folders": ["D:/Work/"], "fields": _fields()})
    inner = profiles.save_profile({"name": "Inner", "folders": ["D:/Work/ClientA/"], "fields": _fields()})
    warnings = " ".join(inner["warnings"])
    assert "巢狀" in warnings
    # Inner was added later in the global file, so it currently wins.
    assert "Inner" in warnings

    # fix_profile_order on Outer moves its includeIf to the file end: Outer wins.
    profiles.fix_profile_order("outer")
    outer = next(item for item in profiles.list_profiles() if item["id"] == "outer")
    inner = next(item for item in profiles.list_profiles() if item["id"] == "inner")
    assert "目前「Outer」優先" in " ".join(inner["warnings"])
    assert "目前「Outer」優先" in " ".join(outer["warnings"])


def test_override_detection_and_fix(git_env, git_cli):
    saved = profiles.save_profile({
        "name": "Client A",
        "folders": ["D:/Work/ClientA"],
        "fields": _fields(**{"commit.gpgsign": "true"}),
    })
    assert saved["folders"][0]["overridden_keys"] == []

    # commit.gpgsign has no earlier [commit] section, so git appends it after
    # the includeIf line and shadows the profile value (SPEC-1.2 section 4.4).
    git_cli("config", "--global", "commit.gpgsign", "false")
    item = next(p for p in profiles.list_profiles() if p["id"] == "client-a")
    assert item["folders"][0]["overridden_keys"] == ["commit.gpgsign"]
    assert any("蓋掉" in warning for warning in item["warnings"])

    fixed = profiles.fix_profile_order("client-a")
    assert fixed == ["D:/Work/ClientA/"]
    item = next(p for p in profiles.list_profiles() if p["id"] == "client-a")
    assert item["folders"][0]["overridden_keys"] == []
    # The fix only reorders: the global value itself is untouched and comments kept.
    assert git_cli("config", "--global", "--no-includes", "--get", "commit.gpgsign").stdout.strip() == "false"
    assert "# user comment: keep me" in (git_env / "home" / ".gitconfig").read_text(encoding="utf-8")


def test_external_profile_is_listed_and_delete_keeps_file(git_env, git_cli):
    external_file = git_env / "my-own.gitconfig"
    git_cli("config", "--file", str(external_file), "user.name", "Handwritten")
    git_cli(
        "config", "--global",
        "includeIf.gitdir/i:D:/Hand/Written/.path", str(external_file),
    )
    item = next(p for p in profiles.list_profiles() if p["kind"] == "external")
    assert item["fields"]["user.name"] == "Handwritten"
    assert item["folders"][0]["folder"] == "D:/Hand/Written/"
    assert any("external" in warning for warning in item["warnings"])

    # Editing an external profile keeps its file path and backs it up first.
    edited = profiles.save_profile({
        "id": item["id"], "name": "Handwritten",
        "folders": ["D:/Hand/Written/"], "fields": {"user.name": "Handwritten v2"},
    })
    assert edited["path"] == str(external_file)
    assert edited["fields"]["user.name"] == "Handwritten v2"
    assert list(profiles.backups_dir().glob("my-own.gitconfig.*"))

    profiles.delete_profile(item["id"])
    assert profiles.read_include_if() == []
    assert external_file.is_file()  # external file itself is never deleted


def test_unsupported_condition_is_read_only(git_env, git_cli):
    git_cli("config", "--global", "includeIf.onbranch:main.path", str(git_env / "branch.gitconfig"))
    item = next(p for p in profiles.list_profiles() if p["kind"] == "unsupported")
    assert "不支援" in item["name"]
    with pytest.raises(profiles.ProfileError):
        profiles.save_profile({"id": item["id"], "name": "x", "folders": ["D:/x"], "fields": _fields()})
    with pytest.raises(profiles.ProfileError):
        profiles.delete_profile(item["id"])


def test_gitdir_without_i_is_read_as_folder(git_env, git_cli):
    external_file = git_env / "plain.gitconfig"
    git_cli("config", "--file", str(external_file), "user.email", "p@example.com")
    git_cli("config", "--global", "includeIf.gitdir:D:/Plain/Repo/.path", str(external_file))
    item = next(p for p in profiles.list_profiles() if p["kind"] == "external")
    assert item["folders"][0]["folder"] == "D:/Plain/Repo/"
    assert item["folders"][0]["condition"] == "gitdir:D:/Plain/Repo/"


def test_missing_folder_warns(git_env):
    saved = profiles.save_profile({"name": "Ghost", "folders": ["Q:/Nope/"], "fields": _fields()})
    assert any("資料夾不存在" in warning for warning in saved["warnings"])


def test_validation_errors(git_env):
    with pytest.raises(profiles.ProfileError, match="名稱"):
        profiles.save_profile({"name": "", "folders": ["D:/a"], "fields": _fields()})
    with pytest.raises(profiles.ProfileError, match="資料夾"):
        profiles.save_profile({"name": "X", "folders": [], "fields": _fields()})
    with pytest.raises(profiles.ProfileError, match="@"):
        profiles.save_profile({"name": "X", "folders": ["D:/a"], "fields": _fields(**{"user.email": "nope"})})
    with pytest.raises(profiles.ProfileError, match="fingerprint"):
        profiles.save_profile({"name": "X", "folders": ["D:/a"], "fields": _fields(**{"user.signingkey": "ABCD"})})


def test_backup_keeps_most_recent_twenty(git_env):
    source = git_env / "big.gitconfig"
    for index in range(25):
        source.write_text(f"# version {index}\n", encoding="utf-8")
        assert profiles.backup_file(source) is not None
    remaining = list(profiles.backups_dir().glob("big.gitconfig.*"))
    assert len(remaining) == 20
    contents = {item.read_text(encoding="utf-8").strip() for item in remaining}
    assert "# version 24" in contents  # the newest backup always survives


def test_missing_global_file_is_tolerated(git_env, monkeypatch):
    (git_env / "home" / ".gitconfig").unlink()
    assert profiles.read_include_if() == []
    assert profiles.global_file_order() == []
    saved = profiles.save_profile({"name": "Fresh", "folders": ["D:/Fresh/"], "fields": _fields()})
    assert saved["folders"][0]["folder"] == "D:/Fresh/"


def test_ssh_command_build_and_parse():
    built = profiles.build_ssh_command(r"C:\Users\alice\.ssh\id_client_a")
    assert built == 'ssh -i "C:/Users/alice/.ssh/id_client_a" -o IdentitiesOnly=yes'

    parsed = profiles.parse_ssh_command(built)
    assert parsed == {"custom": False, "key_path": "C:/Users/alice/.ssh/id_client_a"}

    custom = profiles.parse_ssh_command('ssh -F /c/custom/ssh_config -i "C:/k/id_x"')
    assert custom["custom"] is True
    assert custom["key_path"] == "C:/k/id_x"

    assert profiles.parse_ssh_command("plink -i key") == {"custom": True, "key_path": None}


def test_custom_ssh_command_not_overwritten_by_inherit(git_env):
    profiles.save_profile({
        "name": "SSH Keep",
        "folders": ["D:/Work/Keep/"],
        "fields": {"user.name": "Keep", "core.sshCommand": 'ssh -F /c/custom/config -i "C:/k/id" -o IdentitiesOnly=yes'},
    })
    saved = profiles.save_profile({
        "id": "ssh-keep", "name": "SSH Keep", "folders": ["D:/Work/Keep/"],
        "fields": {"user.name": "Keep"},  # ssh = inherit
    })
    # Custom command must survive an "inherit" unless the user picks a new key.
    assert saved["fields"]["core.sshCommand"].startswith("ssh -F")
    assert saved["ssh_command_custom"] is True

    # A managed-format command CAN be reset to inherit.
    saved = profiles.save_profile({
        "id": "ssh-keep", "name": "SSH Keep", "folders": ["D:/Work/Keep/"],
        "fields": {"user.name": "Keep", "core.sshCommand": profiles.build_ssh_command("C:/k/id2")},
    })
    assert saved["ssh_command_custom"] is False
    saved = profiles.save_profile({
        "id": "ssh-keep", "name": "SSH Keep", "folders": ["D:/Work/Keep/"],
        "fields": {"user.name": "Keep"},
    })
    assert saved["fields"]["core.sshCommand"] is None


# ---------------- real repository scenarios (SPEC-1.2 section 2 table) ----------------

def _make_repo(git_cli, path: Path, name: str = "T", email: str = "t@example.com") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git_cli("init", "-q", "-b", "main", str(path))
    git_cli("-C", str(path), "-c", f"user.name={name}", "-c", f"user.email={email}",
            "commit", "-q", "--allow-empty", "-m", "init")
    return path


@pytest.fixture()
def profiled_folder(git_env, git_cli):
    """Profile covering D-drive sandbox folder with name+email overrides."""
    folder = git_env / "client-a"
    folder.mkdir()
    # The sandbox lives under TEMP; use its real path in the condition.
    profiles.save_profile({
        "name": "Client A",
        "folders": [str(folder)],
        "fields": {"user.name": "Profile Alice", "user.email": "alice@client-a.example.com"},
    })
    return folder


def _value(rows, key: str) -> str:
    return next(row["value"] for row in rows if row["key"] == key)


def test_effective_config_repo_submodule_worktree(git_env, git_cli, profiled_folder: Path):
    inside = _make_repo(git_cli, profiled_folder / "repo")
    result = profiles.check_effective_config(str(inside))
    assert result["is_repo"] is True
    assert _value(result["rows"], "user.name") == "Profile Alice"
    assert _value(result["rows"], "user.email") == "alice@client-a.example.com"
    assert _value(result["rows"], "commit.gpgsign") == ""  # inherit -> unset
    assert result["rows"][0]["origin"]  # --show-origin filled
    assert result["note"] == ""

    # Submodule of the in-folder repo: gitdir is under <main>/.git/modules/... -> applies.
    outside_src = _make_repo(git_cli, git_env / "sub-src")
    git_cli("-c", "protocol.file.allow=always", "-C", str(inside),
            "submodule", "add", "-q", str(outside_src), "sub")
    submodule = inside / "sub"
    result = profiles.check_effective_config(str(submodule))
    assert _value(result["rows"], "user.name") == "Profile Alice"

    # Worktree of the in-folder repo, opened OUTSIDE the folder -> still applies.
    wt_inside_main = git_env / "wt-of-inside"
    git_cli("-C", str(inside), "worktree", "add", "-q", "-b", "wt-a", str(wt_inside_main))
    result = profiles.check_effective_config(str(wt_inside_main))
    assert _value(result["rows"], "user.name") == "Profile Alice"
    assert result["note"] == ""

    # Worktree of an OUTSIDE repo opened INSIDE the folder -> does NOT apply.
    outside_repo = _make_repo(git_cli, git_env / "outside" / "repo")
    wt_outside = profiled_folder / "wt-of-outside"
    git_cli("-C", str(outside_repo), "worktree", "add", "-q", "-b", "wt-b", str(wt_outside))
    result = profiles.check_effective_config(str(wt_outside))
    assert _value(result["rows"], "user.name") == "Global Alice"
    assert "worktree" in result["note"]


def test_effective_config_non_repo_folder(git_env, profiled_folder: Path):
    plain = profiled_folder / "not-a-repo"
    plain.mkdir()
    result = profiles.check_effective_config(str(plain))
    assert result["is_repo"] is False
    assert "不是 git repo" in result["note"]


def test_effective_config_missing_folder_raises(git_env):
    with pytest.raises(NotADirectoryError):
        profiles.check_effective_config(str(git_env / "does-not-exist"))
