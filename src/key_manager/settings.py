from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


APP_SETTINGS_DIR = "KeyManager"
SETTINGS_FILE = "settings.json"

# Dev-Toolbox web server overrides this to %LOCALAPPDATA%\DevToolbox\key-manager
# (TOOL-SPEC dataDir). Desktop mode leaves it None and keeps using KeyManager\.
_settings_dir_override: Path | None = None


def set_settings_dir(directory: str | Path | None) -> None:
    global _settings_dir_override
    _settings_dir_override = Path(directory) if directory else None


def get_settings_dir() -> Path:
    if _settings_dir_override is not None:
        return _settings_dir_override
    return _local_appdata_dir() / APP_SETTINGS_DIR


def _home_dir() -> Path:
    return Path.home()


def _local_appdata_dir() -> Path:
    value = os.environ.get("LOCALAPPDATA", "").strip()
    if value:
        return Path(value)
    # Windows-only product, but keep a deterministic fallback for tests/dev.
    return _home_dir() / "AppData" / "Local"


def settings_path() -> Path:
    return get_settings_dir() / SETTINGS_FILE


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

VALID_THEMES = {"light", "dark", "system"}


def get_theme() -> str:
    value = _load().get("theme")
    return value if isinstance(value, str) and value in VALID_THEMES else "system"


def set_theme(theme: str) -> None:
    value = str(theme).strip().lower()
    if value not in VALID_THEMES:
        raise ValueError("Theme must be light, dark or system")
    data = _load()
    data["theme"] = value
    _save(data)


def get_managed_agent_env() -> dict[str, str]:
    value = _load().get("managed_ssh_agent")
    if not isinstance(value, dict):
        return {}
    sock = value.get("SSH_AUTH_SOCK")
    pid = value.get("SSH_AGENT_PID")
    if not isinstance(sock, str) or not sock.strip():
        return {}
    if not isinstance(pid, str) or not pid.isdigit():
        return {}
    return {"SSH_AUTH_SOCK": sock, "SSH_AGENT_PID": pid}


def set_managed_agent_env(env: dict[str, str]) -> None:
    sock = str(env.get("SSH_AUTH_SOCK", "")).strip()
    pid = str(env.get("SSH_AGENT_PID", "")).strip()
    if not sock or not pid.isdigit():
        raise ValueError("Invalid managed SSH Agent environment")
    data = _load()
    data["managed_ssh_agent"] = {
        "SSH_AUTH_SOCK": sock,
        "SSH_AGENT_PID": pid,
    }
    _save(data)


def clear_managed_agent_env() -> None:
    data = _load()
    data.pop("managed_ssh_agent", None)
    _save(data)

