"""Folder-scoped Git settings via global includeIf (SPEC-1.2).

Every read/write of Git settings goes through the git CLI so the user's own
comments and layout in the global .gitconfig survive (SPEC-1.2 section 2).
The global file itself is never parsed or rewritten as text.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from key_manager.command import run_command
from key_manager.git.git_for_windows import find_git_for_windows
from key_manager.settings import get_settings_dir

# Git keys a Profile can carry (SPEC-1.2 section 3.3). Absent key = inherit.
PROFILE_KEYS = (
    "user.name",
    "user.email",
    "user.signingkey",
    "commit.gpgsign",
    "tag.gpgSign",
    "core.sshCommand",
)
GLOBAL_ONLY_KEYS = ("gpg.format", "gpg.program")

_BACKUP_KEEP = 20
_FULL_FINGERPRINT = re.compile(r"^[A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?$")
_SSH_COMMAND = re.compile(
    r'^ssh\s+-i\s+"(?P<key>[^"]+)"\s+-o\s+IdentitiesOnly=yes\s*$',
    re.IGNORECASE,
)
_ERE_SPECIAL = re.compile(r"([.^$\\[\](){}*+?|])")
_TIMESTAMP_SUFFIX = re.compile(r"\.(\d{8}-\d{6})(?:-(\d+))?$")

_NOT_A_REPO_NOTE = "這裡不是 git repo，設定只會在 repo 內生效"
_WORKTREE_NOTE = (
    "這是 worktree，且它的主 repo 不在任何 Profile 資料夾內；"
    "includeIf 以主 repo 的 .git 位置判斷，所以 Profile 不會套用"
)


class ProfileError(RuntimeError):
    """User-facing failure while managing folder profiles."""


# ---------------- paths ----------------

def global_config_path() -> Path:
    value = os.environ.get("GIT_CONFIG_GLOBAL", "").strip()
    if value:
        return Path(value).expanduser()
    return Path.home() / ".gitconfig"


def profiles_dir() -> Path:
    return get_settings_dir() / "profiles"


def backups_dir() -> Path:
    return get_settings_dir() / "backups"


def profiles_json_path() -> Path:
    return get_settings_dir() / "profiles.json"


def _require_git() -> Path:
    git = find_git_for_windows()
    if git is None:
        raise ProfileError("找不到 Git for Windows，無法讀寫 Git 設定")
    return git


# ---------------- normalisation helpers ----------------

def normalize_folder(raw: str) -> str:
    """Backslashes to slashes, collapse duplicates, ensure trailing slash."""
    text = str(raw).strip().strip('"').strip("'")
    if not text:
        raise ProfileError("資料夾路徑不可為空白")
    text = text.replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if not text.endswith("/"):
        text += "/"
    return text


def folder_key(text: str) -> str:
    """Comparable folder/path token: slashes, no trailing slash, casefolded."""
    return str(text).replace("\\", "/").rstrip("/").casefold()


_folder_key = folder_key


def paths_equivalent(left: str, right: str) -> bool:
    """Compare file paths ignoring case and slash direction (Windows rules)."""
    a = os.path.expanduser(str(left).strip().strip('"')).replace("\\", "/").rstrip("/").casefold()
    b = os.path.expanduser(str(right).strip().strip('"')).replace("\\", "/").rstrip("/").casefold()
    return bool(a) and a == b


def is_managed_profile_path(path: str) -> bool:
    try:
        Path(path).resolve().relative_to(profiles_dir().resolve())
        return True
    except (OSError, ValueError):
        return False


def classify_condition(condition: str) -> tuple[str, str]:
    """Return ("managed"|"folder"|"unsupported", folder part or "")."""
    lowered = condition.strip().lower()
    if lowered.startswith("gitdir/i:"):
        return "managed", condition.strip()[len("gitdir/i:"):]
    if lowered.startswith("gitdir:"):
        return "folder", condition.strip()[len("gitdir:"):]
    return "unsupported", ""


def condition_folder(condition: str) -> str:
    _, part = classify_condition(condition)
    if not part:
        return ""
    trimmed = part.rstrip("/")
    if trimmed.endswith("/**"):
        trimmed = trimmed[: -len("/**")]
    if not trimmed:
        return ""
    return normalize_folder(trimmed)


# ---------------- backup ----------------

def _backup_target(directory: Path, name: str) -> Path:
    """Unique backups/<name>.<yyyyMMdd-HHmmss>[-NN]; counters keep time order."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pattern = re.compile(rf"^{re.escape(name)}\.(\d{{8}}-\d{{6}})(?:-(\d+))?$")
    highest = 0
    if directory.is_dir():
        for item in directory.iterdir():
            match = pattern.match(item.name)
            if match and match.group(1) == stamp:
                highest = max(highest, int(match.group(2) or 1))
    if highest == 0:
        return directory / f"{name}.{stamp}"
    return directory / f"{name}.{stamp}-{highest + 1:02d}"


def _backup_sort_key(file_name: str, name: str) -> tuple[str, int]:
    """Chronological sort key parsed from the backup suffix (stamp, counter)."""
    match = _TIMESTAMP_SUFFIX.match(file_name[len(name):])
    if not match:
        return ("", 0)
    return (match.group(1), int(match.group(2) or 1))


def backup_file(path: Path) -> Path | None:
    """Copy a file into backups/ before any write (SPEC-1.2 section 3.4)."""
    path = Path(path)
    if not path.is_file():
        return None
    directory = backups_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = _backup_target(directory, path.name)
    shutil.copy2(path, target)
    _prune_backups(path.name)
    return target


# ---------------- backup browse / preview / restore (1.2.2) ----------------

_BACKUP_PREVIEW_LIMIT = 200_000


def _split_backup_name(file_name: str) -> tuple[str, str] | None:
    """Split '<base>.<yyyyMMdd-HHmmss>[-NN]' into (base, stamp); None if foreign."""
    match = _TIMESTAMP_SUFFIX.search(file_name)
    if not match:
        return None
    return file_name[: match.start()], match.group(1)


def _backup_path(name: str) -> Path:
    """Validate a backup file name and return its path inside backups/."""
    file_name = Path(str(name)).name
    if file_name != str(name) or _split_backup_name(file_name) is None:
        raise ProfileError(f"無效的備份檔名：{name}")
    backup = backups_dir() / file_name
    if not backup.is_file():
        raise ProfileError(f"找不到備份檔：{file_name}")
    return backup


def _resolve_backup_target(backup_name: str) -> tuple[Path | None, str, str]:
    """Map backups/<base>.<stamp> back to the file it can restore.

    Returns (target_or_None, base, kind) with kind 'global' (the global
    .gitconfig), 'profile' (a file inside profiles_dir) or 'unknown'
    (e.g. an external includeIf target that no longer exists).
    """
    split = _split_backup_name(backup_name)
    if split is None:
        return None, "", "unknown"
    base = split[0]
    if base.casefold() == global_config_path().name.casefold():
        return global_config_path(), base, "global"
    candidate = profiles_dir() / base
    if candidate.is_file():
        return candidate, base, "profile"
    return None, base, "unknown"


def list_backups() -> list[dict[str, Any]]:
    """Backup files, newest first, each mapped to its restore target."""
    directory = backups_dir()
    if not directory.is_dir():
        return []
    meta = load_profile_meta()
    entries: list[tuple[tuple[str, int], dict[str, Any]]] = []
    for item in directory.iterdir():
        if not item.is_file():
            continue
        match = _TIMESTAMP_SUFFIX.search(item.name)
        if match is None:
            continue
        target, _base, kind = _resolve_backup_target(item.name)
        profile_id = target.stem if (target is not None and kind == "profile") else ""
        try:
            stat = item.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size = stat.st_size
        except OSError:
            modified, size = "", 0
        entries.append(
            (
                (match.group(1), int(match.group(2) or 1)),
                {
                    "name": item.name,
                    "base": item.name[: match.start()],
                    "target": kind,
                    "profile_id": profile_id,
                    "profile_name": (meta.get(profile_id) or {}).get("name", "") if profile_id else "",
                    "path": str(target) if target else "",
                    "restorable": bool(target is not None and target.is_file()),
                    "size": size,
                    "modified": modified,
                },
            )
        )
    entries.sort(key=lambda pair: (pair[0][0], pair[0][1], pair[1]["name"]), reverse=True)
    return [entry for _key, entry in entries]


def read_backup(name: str) -> dict[str, Any]:
    """Preview a backup file's content (truncated for very large files)."""
    backup = _backup_path(name)
    payload = backup.read_bytes()
    text = payload.decode("utf-8", errors="replace")
    return {
        "name": backup.name,
        "size": len(payload),
        "text": text[:_BACKUP_PREVIEW_LIMIT],
        "truncated": len(payload) > _BACKUP_PREVIEW_LIMIT,
    }


def restore_backup(name: str) -> dict[str, Any]:
    """Restore a backup over its current file (the current file is backed up first)."""
    backup = _backup_path(name)
    target, base, kind = _resolve_backup_target(backup.name)
    if target is None:
        raise ProfileError(
            f"無法判斷 {base} 的還原目標（檔案可能已被移除或位於 Profile 之外），"
            "請改用「開啟資料夾」將備份檔手動複製回原位"
        )
    if not target.is_file():
        raise ProfileError(f"目標檔案已不存在：{target}")
    try:
        backup_file(target)  # the pre-restore snapshot makes the restore rollback-able
    except OSError as exc:
        raise ProfileError(f"還原前無法為目前檔案建立備份（目標未被改動）：{exc}") from exc
    payload = backup.read_bytes()
    tmp = target.with_name(target.name + ".key-manager-restore.tmp")
    try:
        tmp.write_bytes(payload)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return {"name": backup.name, "target": str(target), "kind": kind, "size": len(payload)}


def move_to_backups(path: Path) -> Path | None:
    path = Path(path)
    if not path.is_file():
        return None
    directory = backups_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = _backup_target(directory, path.name)
    shutil.move(str(path), str(target))
    _prune_backups(path.name)
    return target


def _prune_backups(name: str) -> None:
    directory = backups_dir()
    if not directory.is_dir():
        return
    candidates = [
        item for item in directory.iterdir()
        if item.name.startswith(f"{name}.") and _TIMESTAMP_SUFFIX.match(item.name[len(name):])
    ]
    candidates.sort(key=lambda item: _backup_sort_key(item.name, name), reverse=True)
    for stale in candidates[_BACKUP_KEEP:]:
        try:
            stale.unlink()
        except OSError:
            pass


# ---------------- profiles.json (display meta only) ----------------

def load_profile_meta() -> dict[str, dict[str, Any]]:
    import json

    path = profiles_json_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        return {}
    meta = {}
    for key, value in data["profiles"].items():
        if isinstance(value, dict):
            meta[str(key)] = {
                "name": str(value.get("name", "")),
                "note": str(value.get("note", "")),
            }
    return meta


def save_profile_meta(meta: dict[str, dict[str, Any]]) -> None:
    import json

    path = profiles_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "profiles": meta}
    temp = path.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


# ---------------- git CLI reads ----------------

def _run_git(args: list[str], timeout: float = 20.0):
    result = run_command([str(_require_git()), *args], timeout=timeout)
    return result


def _check(result, action: str):
    if result.returncode not in (0, 1):
        raise ProfileError(result.stderr.strip() or f"Git {action} 失敗")
    return result


def read_include_if() -> list[dict[str, str]]:
    """All includeIf entries in the global file (SPEC-1.2 section 2 read form)."""
    if not global_config_path().is_file():
        return []
    result = _check(
        _run_git(["config", "--global", "--get-regexp", "-z", "^includeif\\."]),
        "讀取 includeIf",
    )
    entries: list[dict[str, str]] = []
    for record in result.stdout.split("\x00"):
        key, separator, value = record.partition("\n")
        if not separator:
            continue
        lowered = key.lower()
        if not lowered.startswith("includeif.") or not lowered.endswith(".path"):
            continue
        condition = key[len("includeif."):-len(".path")]
        entries.append({"condition": condition, "profile_path": value.strip(), "key": key})
    return entries


def global_file_order() -> list[tuple[str, str]]:
    """(key, value) pairs in global-file order, includes not expanded (4.4)."""
    if not global_config_path().is_file():
        return []
    result = _check(
        _run_git(["config", "--global", "--no-includes", "--list", "-z"]),
        "讀取全域設定順序",
    )
    pairs: list[tuple[str, str]] = []
    for record in result.stdout.split("\x00"):
        key, separator, value = record.partition("\n")
        if separator:
            pairs.append((key, value))
    return pairs


def read_profile_file(path: Path) -> dict[str, str]:
    """Current values of PROFILE_KEYS inside a Profile file (git CLI only)."""
    path = Path(path)
    if not path.is_file():
        return {}
    result = _check(
        _run_git(["config", "--file", str(path), "--list", "-z"]),
        f"讀取 Profile 檔：{path.name}",
    )
    values: dict[str, str] = {}
    for record in result.stdout.split("\x00"):
        key, separator, value = record.partition("\n")
        if not separator:
            continue
        if key.lower() in {item.lower() for item in PROFILE_KEYS}:
            values[key.lower()] = value
    return values


def read_global_value(key: str) -> str:
    """Value of a key in the global file itself (no include expansion)."""
    result = _check(_run_git(["config", "--global", "--no-includes", "--get", key]), f"讀取 {key}")
    return result.stdout.strip() if result.returncode == 0 else ""


# ---------------- git CLI writes ----------------

def _include_key(condition: str) -> str:
    return f"includeIf.{condition}.path"


def _escape_ere(text: str) -> str:
    return _ERE_SPECIAL.sub(r"\\\1", text)


def add_include_if(condition: str, profile_path: str) -> None:
    backup_file(global_config_path())
    _check(
        _run_git(["config", "--global", _include_key(condition), str(profile_path)]),
        "新增資料夾設定",
    )


def remove_include_if(condition: str, profile_path: str | None = None) -> None:
    backup_file(global_config_path())
    args = ["config", "--global", "--unset", _include_key(condition)]
    if profile_path:
        args.append(_escape_ere(str(profile_path)))
    result = _run_git(args)
    if result.returncode not in (0, 5):
        raise ProfileError(result.stderr.strip() or "移除資料夾設定失敗")
    # Drop the section when nothing is left under this condition.
    remaining = [
        item for item in read_include_if()
        if item["condition"].casefold() == condition.casefold()
    ]
    if not remaining:
        _run_git(["config", "--global", "--remove-section", f"includeIf.{condition}"])


# ---------------- ssh command build/parse ----------------

def build_ssh_command(private_path: str | Path) -> str:
    posix = str(private_path).replace("\\", "/")
    return f'ssh -i "{posix}" -o IdentitiesOnly=yes'


def parse_ssh_command(value: str) -> dict[str, Any]:
    """Recognise the Key Manager format; anything else is a custom command."""
    text = str(value).strip()
    match = _SSH_COMMAND.match(text)
    if match:
        return {"custom": False, "key_path": match.group("key")}
    if text.lower().startswith("ssh") or text.lower().startswith('"ssh'):
        found = re.search(r'-i\s+"(?P<quoted>[^"]+)"|-i\s+(?P<bare>[^\s"]+)', text, re.IGNORECASE)
        if found:
            return {"custom": True, "key_path": found.group("quoted") or found.group("bare")}
    return {"custom": True, "key_path": None}


# ---------------- profile listing ----------------

def _external_id(profile_path: str) -> str:
    digest = hashlib.sha1(_folder_key(profile_path).encode("utf-8")).hexdigest()
    return f"ext-{digest[:10]}"


def _new_profile_id(name: str, folders: list[str], taken: set[str]) -> str:
    def slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40].strip("-")

    base = slug(name) or (slug(folders[0]) if folders else "") or "profile"
    candidate = base
    counter = 2
    while candidate in taken or (profiles_dir() / f"{candidate}.gitconfig").exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _position_map(order: list[tuple[str, str]]) -> dict[tuple[str, str], int]:
    """(condition casefold, path casefold) -> line position in the global file."""
    positions: dict[tuple[str, str], int] = {}
    for index, (key, value) in enumerate(order):
        lowered = key.lower()
        if lowered.startswith("includeif.") and lowered.endswith(".path"):
            condition = key[len("includeif."):-len(".path")]
            positions.setdefault((condition.casefold(), value.strip().casefold()), index)
    return positions


def _overridden_keys(order: list[tuple[str, str]], position: int, keys: list[str]) -> list[str]:
    """Keys that also appear after the includeIf line inside the global file."""
    hits: list[str] = []
    wanted = {key.lower() for key in keys}
    for index, (key, _value) in enumerate(order):
        if index > position and key.lower() in wanted and key.lower() not in hits:
            hits.append(key.lower())
    return hits


def list_profiles() -> list[dict[str, Any]]:
    """Folder profiles merged from the global file, profile files and meta."""
    entries = read_include_if()
    order = global_file_order()
    positions = _position_map(order)
    meta = load_profile_meta()

    grouped: dict[str, dict[str, Any]] = {}
    result: list[dict[str, Any]] = []
    for entry in entries:
        condition = entry["condition"]
        profile_path = entry["profile_path"]
        kind, folder_part = classify_condition(condition)
        if kind == "unsupported" or not profile_path:
            profile_id = "cond-" + hashlib.sha1(condition.casefold().encode()).hexdigest()[:10]
            item = grouped.get(profile_id)
            if item is None:
                item = {
                    "id": profile_id, "kind": "unsupported",
                    "name": f"不支援的條件：{condition}", "note": "", "path": profile_path,
                    "folders": [], "fields": {}, "warnings": ["不支援的條件（唯讀，Key Manager 不會修改它）"],
                    "ssh_command_custom": False,
                }
                grouped[profile_id] = item
                result.append(item)
            item["folders"].append({
                "folder": "", "condition": condition, "overridden_keys": [],
                "position": positions.get((condition.casefold(), profile_path.casefold())),
            })
            continue

        managed = is_managed_profile_path(profile_path)
        profile_id = Path(profile_path).stem if managed else _external_id(profile_path)
        item = grouped.get(profile_id)
        if item is None:
            display = meta.get(profile_id, {}).get("name", "") or Path(profile_path).stem
            item = {
                "id": profile_id,
                "kind": "managed" if managed else "external",
                "name": display, "note": meta.get(profile_id, {}).get("note", ""),
                "path": profile_path, "folders": [], "fields": {}, "warnings": [],
                "ssh_command_custom": False,
            }
            grouped[profile_id] = item
            result.append(item)
        item["folders"].append({
            "folder": condition_folder(condition), "condition": condition, "overridden_keys": [],
            "position": positions.get((condition.casefold(), profile_path.casefold())),
        })

    for item in result:
        if item["kind"] == "unsupported":
            continue
        fields = read_profile_file(Path(item["path"])) if item["path"] else {}
        item["fields"] = {key: fields.get(key.lower()) for key in PROFILE_KEYS}
        if item["path"] and not Path(item["path"]).is_file():
            item["warnings"].append(f"Profile 檔不存在：{item['path']}")
        ssh_value = fields.get("core.sshcommand", "")
        if ssh_value:
            item["ssh_command_custom"] = parse_ssh_command(ssh_value)["custom"]
        active_keys = [key for key in PROFILE_KEYS if fields.get(key.lower()) is not None]
        for folder in item["folders"]:
            position = folder["position"]
            if position is None:
                continue
            folder["overridden_keys"] = _overridden_keys(order, position, active_keys)
            if folder["overridden_keys"]:
                item["warnings"].append(
                    f"{folder['folder']} 的 {'、'.join(folder['overridden_keys'])} 在全域檔中位於 includeIf 之後，會被蓋掉"
                )
        if item["kind"] == "external":
            item["warnings"].insert(0, "external：這是使用者手寫 includeIf 指向的檔案，第一次編輯前請先確認")
        for folder in item["folders"]:
            if folder["folder"] and not Path(os.path.expanduser(folder["folder"].rstrip("/"))).exists():
                item["warnings"].append(f"資料夾不存在：{folder['folder']}")

    _add_nested_warnings(result, grouped)
    return result


def _add_nested_warnings(profiles: list[dict[str, Any]], grouped: dict[str, dict[str, Any]]) -> None:
    placed: list[tuple[str, dict[str, Any]]] = []
    for item in profiles:
        if item["kind"] == "unsupported":
            continue
        for folder in item["folders"]:
            if folder["folder"]:
                placed.append((_folder_key(folder["folder"]), item))
    for inner_key, inner in placed:
        for outer_key, outer in placed:
            if inner is outer or not outer_key or inner_key == outer_key:
                continue
            if not inner_key.startswith(f"{outer_key}/"):
                continue
            inner_pos = next((f["position"] for f in inner["folders"] if _folder_key(f["folder"]) == inner_key), None)
            outer_pos = next((f["position"] for f in outer["folders"] if _folder_key(f["folder"]) == outer_key), None)
            if inner_pos is not None and outer_pos is not None:
                winner = inner if inner_pos > outer_pos else outer
                priority = f"目前「{winner['name']}」優先"
            else:
                priority = "優先順序無法判斷"
            message = (
                f"巢狀資料夾：與「{outer['name']}」的 {outer_key}/ 重疊，兩個都會套用，"
                f"全域檔中位置較後面的那個優先；{priority}"
            )
            for item in (inner, outer):
                if message not in item["warnings"]:
                    item["warnings"].append(message)


# ---------------- profile save/delete ----------------

def _validate_profile_fields(fields: dict[str, Any]) -> dict[str, str | None]:
    """Normalise the six dialog fields; missing or None = inherit (unset)."""
    cleaned: dict[str, str | None] = {}
    name = fields.get("user.name")
    if name is not None:
        name = " ".join(str(name).split())
        if not name:
            raise ProfileError("user.name 不可為空白（要沿用全域請選「沿用全域」）")
    cleaned["user.name"] = name or None
    email = fields.get("user.email")
    if email is not None:
        email = str(email).strip()
        if not email:
            raise ProfileError("user.email 不可為空白（要沿用全域請選「沿用全域」）")
        if "@" not in email:
            raise ProfileError("Email 必須包含 @")
    cleaned["user.email"] = email or None
    signing = fields.get("user.signingkey")
    if signing is not None:
        signing = str(signing).replace(" ", "").strip()
        if not _FULL_FINGERPRINT.fullmatch(signing):
            raise ProfileError("簽章 Key 必須是完整的 GPG fingerprint")
    cleaned["user.signingkey"] = signing or None
    for key in ("commit.gpgsign", "tag.gpgSign"):
        value = fields.get(key)
        if value is None:
            cleaned[key] = None
            continue
        text = str(value).strip().lower()
        if text not in ("true", "false"):
            raise ProfileError(f"{key} 只能是 true 或 false")
        cleaned[key] = text
    ssh = fields.get("core.sshCommand")
    if ssh is not None:
        ssh = str(ssh).strip()
        if not ssh:
            raise ProfileError("core.sshCommand 不可為空白")
    cleaned["core.sshCommand"] = ssh or None
    return cleaned


def save_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Create or update a profile: profile file + includeIf lines + meta."""
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ProfileError("Profile 名稱不可為空白")
    note = str(payload.get("note", "")).strip()

    folders: list[str] = []
    seen: set[str] = set()
    for raw in payload.get("folders", []):
        normalized = normalize_folder(raw)
        if _folder_key(normalized) not in seen:
            seen.add(_folder_key(normalized))
            folders.append(normalized)
    if not folders:
        raise ProfileError("至少需要一個資料夾")

    existing = list_profiles()
    existing_by_id = {item["id"]: item for item in existing}
    profile_id = str(payload.get("id") or "").strip()

    if profile_id:
        target = existing_by_id.get(profile_id)
        if target is None:
            raise ProfileError(f"找不到 Profile：{profile_id}")
        if target["kind"] == "unsupported":
            raise ProfileError("不支援的條件無法編輯")
        profile_path = target["path"]
    else:
        taken = set(existing_by_id)
        profile_id = _new_profile_id(name, folders, taken)
        profile_path = str(profiles_dir() / f"{profile_id}.gitconfig").replace("\\", "/")

    # Same folder must not live in two profiles (SPEC-1.2 section 4.2).
    for item in existing:
        if item["id"] == profile_id or item["kind"] == "unsupported":
            continue
        for folder in item["folders"]:
            if folder["folder"] and _folder_key(folder["folder"]) in seen:
                raise ProfileError(
                    f"資料夾 {folder['folder']} 已被「{item['name']}」使用，請先從該 Profile 移除"
                )

    fields = _validate_profile_fields(dict(payload.get("fields", {})))

    # Keep a custom sshCommand unless the user picked a new key or inherit was
    # explicitly confirmed for a non-custom value (SPEC-1.2 section 3.3).
    current = read_profile_file(Path(profile_path)) if profile_path else {}
    current_ssh = current.get("core.sshcommand")
    if fields.get("core.sshCommand") is None and current_ssh and parse_ssh_command(current_ssh)["custom"]:
        fields.pop("core.sshCommand", None)

    target_path = Path(profile_path)
    if target_path.is_file():
        backup_file(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    for key in PROFILE_KEYS:
        if key not in fields:
            continue
        value = fields[key]
        existing_value = current.get(key.lower())
        if value is None:
            if existing_value is None:
                continue
            result = _run_git(["config", "--file", str(target_path), "--unset", key])
            if result.returncode not in (0, 5):
                raise ProfileError(result.stderr.strip() or f"移除 {key} 失敗")
        else:
            result = _run_git(["config", "--file", str(target_path), key, value])
            if result.returncode != 0:
                raise ProfileError(result.stderr.strip() or f"寫入 {key} 失敗")

    # Diff includeIf lines: remove folders no longer listed, add new ones.
    current_entry = existing_by_id.get(profile_id)
    current_conditions = {
        folder["condition"]: folder for folder in (current_entry["folders"] if current_entry else [])
    }
    desired_conditions = {f"gitdir/i:{folder}": folder for folder in folders}

    for condition, folder in current_conditions.items():
        if condition not in desired_conditions:
            remove_include_if(condition, profile_path)
    for condition in desired_conditions:
        if condition not in current_conditions:
            add_include_if(condition, profile_path)

    meta = load_profile_meta()
    meta[profile_id] = {"name": name, "note": note}
    save_profile_meta(meta)

    saved = next((item for item in list_profiles() if item["id"] == profile_id), None)
    if saved is None:
        raise ProfileError("Profile 已寫入但重新讀取時找不到，請檢查全域 .gitconfig")
    return saved


def delete_profile(profile_id: str) -> list[str]:
    """Remove includeIf lines; managed profile files move to backups."""
    existing = list_profiles()
    target = next((item for item in existing if item["id"] == profile_id), None)
    if target is None:
        raise ProfileError(f"找不到 Profile：{profile_id}")
    if target["kind"] == "unsupported":
        raise ProfileError("不支援的條件請手動在全域 .gitconfig 中處理")

    removed: list[str] = []
    for folder in target["folders"]:
        remove_include_if(folder["condition"], target["path"])
        removed.append(folder["folder"] or folder["condition"])
    if target["kind"] == "managed" and target["path"]:
        move_to_backups(Path(target["path"]))
    meta = load_profile_meta()
    meta.pop(profile_id, None)
    save_profile_meta(meta)
    return removed


def fix_profile_order(profile_id: str) -> list[str]:
    """Move a profile's includeIf sections to the end of the global file."""
    target = next((item for item in list_profiles() if item["id"] == profile_id), None)
    if target is None:
        raise ProfileError(f"找不到 Profile：{profile_id}")
    if target["kind"] == "unsupported":
        raise ProfileError("不支援的條件無法修正順序")
    fixed: list[str] = []
    for folder in target["folders"]:
        remove_include_if(folder["condition"], target["path"])
        add_include_if(folder["condition"], target["path"])
        fixed.append(folder["folder"] or folder["condition"])
    return fixed


# ---------------- effective value check (SPEC-1.2 section 4.3) ----------------

def _unescape_origin(origin: str) -> str:
    text = origin
    if text.startswith("file:"):
        text = text[len("file:"):]
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1].replace("\\\\", "\\").replace('\\"', '"')
    return text


def check_effective_config(folder: str) -> dict[str, Any]:
    git = _require_git()
    target = Path(str(folder)).expanduser()
    if not target.is_dir():
        raise NotADirectoryError(f"找不到資料夾：{target}")
    probe = run_command([str(git), "-C", str(target), "rev-parse", "--is-inside-work-tree"], timeout=15)
    if probe.returncode != 0:
        return {"is_repo": False, "folder": str(target), "rows": [], "note": _NOT_A_REPO_NOTE}

    rows: list[dict[str, Any]] = []
    for key in PROFILE_KEYS:
        result = run_command(
            [str(git), "-C", str(target), "config", "--show-origin", "--show-scope", "--get", key],
            timeout=15,
        )
        if result.returncode == 0:
            scope, _, rest = result.stdout.strip().partition("\t")
            origin, _, value = rest.partition("\t")
            rows.append({"key": key, "value": value, "scope": scope, "origin": _unescape_origin(origin)})
        elif result.returncode == 1:
            rows.append({"key": key, "value": "", "scope": "", "origin": ""})
        else:
            raise ProfileError(result.stderr.strip() or f"讀取 {key} 失敗")

    note = ""
    folders = [condition_folder(item["condition"]) for item in read_include_if()]
    folders = [item for item in folders if item]
    inside_profile = any(
        _folder_key(str(target)).startswith(_folder_key(item)) for item in folders
    )
    common = run_command(
        [str(git), "-C", str(target), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        timeout=15,
    )
    if common.returncode == 0:
        common_dir = common.stdout.strip().replace("\\", "/").rstrip("/").casefold()
        common_inside = any(common_dir.startswith(_folder_key(item)) for item in folders)
        git_dir = run_command(
            [str(git), "-C", str(target), "rev-parse", "--absolute-git-dir"], timeout=15
        )
        is_worktree = (
            git_dir.returncode == 0
            and git_dir.stdout.strip().casefold().rstrip("/") != common_dir
        )
        if is_worktree and not common_inside:
            note = _WORKTREE_NOTE
    return {"is_repo": True, "folder": str(target), "rows": rows, "note": note}
