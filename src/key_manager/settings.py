from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


APP_SETTINGS_DIR = "KeyManager"
SETTINGS_FILE = "settings.json"


def _home_dir() -> Path:
    return Path.home()


def _local_appdata_dir() -> Path:
    value = os.environ.get("LOCALAPPDATA", "").strip()
    if value:
        return Path(value)
    # Windows-only product, but keep a deterministic fallback for tests/dev.
    return _home_dir() / "AppData" / "Local"


def settings_path() -> Path:
    return _local_appdata_dir() / APP_SETTINGS_DIR / SETTINGS_FILE


def default_ssh_dir() -> Path:
    return _home_dir() / ".ssh"


def _load() -> dict[str, Any]:
    path = settings_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def get_ssh_dir() -> Path:
    value = _load().get("ssh_dir")
    if isinstance(value, str) and value.strip():
        return Path(value).expanduser()
    return default_ssh_dir()


def set_ssh_dir(directory: str | Path) -> None:
    raw = str(directory).strip()
    if not raw:
        raise ValueError("SSH Key 路徑不可為空白")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ValueError("SSH Key 路徑必須是絕對路徑")
    if path.exists() and not path.is_dir():
        raise ValueError("SSH Key 路徑必須是資料夾")
    data = _load()
    data["ssh_dir"] = str(path)
    _save(data)


def reset_ssh_dir() -> None:
    data = _load()
    data.pop("ssh_dir", None)
    _save(data)
