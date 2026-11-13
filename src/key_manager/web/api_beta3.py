from __future__ import annotations

from pathlib import Path
from typing import Any

from key_manager.settings import get_ssh_dir, get_theme, reset_ssh_dir, set_ssh_dir, set_theme
from key_manager.git import profiles
from key_manager.gpg.export import armor_public_key
from key_manager.ssh.discovery import discover_ssh_keys
from key_manager.usage import collect_key_usage
from .api import KeyManagerApi as BaseKeyManagerApi


def _ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def _error(exc: Exception, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "error": str(exc) or exc.__class__.__name__, **payload}


def _folder_dialog_type(webview_module: Any) -> Any:
    dialog = getattr(webview_module, "FileDialog", None)
    if dialog is not None and hasattr(dialog, "FOLDER"):
        return dialog.FOLDER
    return webview_module.FOLDER_DIALOG


def _blank_to_none(value: Any) -> str | None:
    text = str(value).strip() if value is not None and not isinstance(value, bool) else value
    if isinstance(text, str) and not text:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return text


class KeyManagerApi(BaseKeyManagerApi):
    """Beta 3 API additions for persistent SSH local-key path settings."""


    def get_theme(self) -> dict[str, Any]:
        return _ok(theme=get_theme())

    def set_theme(self, theme: str) -> dict[str, Any]:
        try:
            set_theme(theme)
            return _ok(theme=get_theme())
        except Exception as exc:
            return _error(exc, theme=get_theme())

    def get_ssh_directory(self) -> dict[str, Any]:
        return _ok(ssh_dir=str(get_ssh_dir()))

    def select_ssh_directory(self) -> dict[str, Any]:
        try:
            window = self._window_getter()
            if window is None:
                raise RuntimeError("視窗尚未初始化")
            try:
                import webview
            except ImportError as exc:
                raise RuntimeError("pywebview 尚未安裝") from exc

            result = window.create_file_dialog(
                _folder_dialog_type(webview),
                directory=str(get_ssh_dir()),
                allow_multiple=False,
            )
            if not result:
                return _ok(cancelled=True, ssh_dir=str(get_ssh_dir()))
            selected = result[0] if isinstance(result, (tuple, list)) else result
            path = Path(str(selected))
            set_ssh_dir(path)
            return _ok(ssh_dir=str(path))
        except Exception as exc:
            return _error(exc, ssh_dir=str(get_ssh_dir()))

    def reset_ssh_directory(self) -> dict[str, Any]:
        try:
            reset_ssh_dir()
            return _ok(ssh_dir=str(get_ssh_dir()))
        except Exception as exc:
            return _error(exc, ssh_dir=str(get_ssh_dir()))

    # ---- Web 模式（瀏覽器）替代對話框 ----

    def browse_directories(self, path: str = "", scan: bool = False,
                           depth: int = 2, limit: int = 50) -> dict[str, Any]:
        """列出資料夾，給瀏覽器內的資料夾選擇器用（ui-kit tb-dirpicker 格式）。

        path 空白時回傳磁碟機清單；scan=True 時在 path 下找 Git Repo（{repos}）。
        回傳：{current, parent, items:[{name, path, hasGit}], truncated} 或 {repos}。
        """
        try:
            raw = str(path or "").strip()
            if scan:
                return _ok(repos=_scan_repos(raw, depth=int(depth), limit=int(limit)))
            if not raw:
                roots = _list_roots()
                items = [{"name": r["name"], "path": r["path"], "hasGit": False} for r in roots]
                return _ok(current="", parent=None, items=items, truncated=False)
            current = Path(raw).expanduser()
            if not current.is_absolute():
                raise ValueError("請輸入完整路徑")
            current = current.resolve()
            if not current.is_dir():
                raise NotADirectoryError(f"找不到資料夾：{current}")
            items: list[dict[str, Any]] = []
            truncated = False
            try:
                entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
            except PermissionError as exc:
                raise PermissionError(f"沒有權限讀取：{current}") from exc
            for entry in entries:
                try:
                    if not entry.is_dir():
                        continue
                    if len(items) >= 500:
                        truncated = True
                        break
                    items.append({"name": entry.name, "path": str(entry),
                                  "hasGit": (entry / ".git").exists()})
                except OSError:
                    continue
            parent = None if current.parent == current else str(current.parent)
            return _ok(current=str(current), parent=parent, items=items, truncated=truncated)
        except Exception as exc:
            return _error(exc, current="", parent=None, items=[], truncated=False)

    def set_ssh_directory(self, path: str) -> dict[str, Any]:
        try:
            set_ssh_dir(Path(str(path)))
            return _ok(ssh_dir=str(get_ssh_dir()))
        except Exception as exc:
            return _error(exc, ssh_dir=str(get_ssh_dir()))

    def get_ssh_public_key_text(self, name: str) -> dict[str, Any]:
        try:
            key = self._ssh_key(name)
            text = key.public_path.read_text(encoding="utf-8")
            return _ok(filename=f"{key.name}.pub", text=text)
        except Exception as exc:
            return _error(exc)

    def get_gpg_public_key_text(self, fingerprint: str) -> dict[str, Any]:
        try:
            self._require_gpg_key(fingerprint)
            text = armor_public_key(fingerprint)
            return _ok(filename="gpg-public-key.asc", text=text)
        except Exception as exc:
            return _error(exc)

    # ---- 資料夾 Git 設定（Profile，SPEC-1.2） ----

    def list_git_profiles(self) -> dict[str, Any]:
        try:
            return _ok(profiles=profiles.list_profiles(), global_path=str(profiles.global_config_path()))
        except Exception as exc:
            return _error(exc, profiles=[])

    def save_git_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = dict(profile or {})
            payload["fields"] = self._profile_fields(payload.get("fields") or {})
            saved = profiles.save_profile(payload)
            return _ok(profile=saved, message=f"資料夾設定「{saved['name']}」已儲存")
        except Exception as exc:
            return _error(exc)

    def delete_git_profile(self, id: str) -> dict[str, Any]:
        try:
            removed = profiles.delete_profile(str(id))
            return _ok(message=f"已移除資料夾設定（{len(removed)} 個資料夾）", removed=removed)
        except Exception as exc:
            return _error(exc)

    def check_effective_git_config(self, folder: str) -> dict[str, Any]:
        try:
            result = profiles.check_effective_config(str(folder))
            return _ok(**result)
        except Exception as exc:
            return _error(exc)

    def fix_profile_order(self, id: str) -> dict[str, Any]:
        try:
            fixed = profiles.fix_profile_order(str(id))
            return _ok(message=f"已將 {len(fixed)} 個資料夾的 includeIf 移到全域檔最後", fixed=fixed)
        except Exception as exc:
            return _error(exc)

    def get_key_usage(self) -> dict[str, Any]:
        try:
            usage = collect_key_usage()
            return _ok(**usage)
        except Exception as exc:
            return _error(exc, ssh={}, gpg={}, notes=[])

    def open_backup_folder(self) -> dict[str, Any]:
        try:
            import os

            directory = profiles.backups_dir()
            directory.mkdir(parents=True, exist_ok=True)
            if os.name == "nt" and self._window_getter() is not None:
                os.startfile(str(directory))  # type: ignore[attr-defined]
            return _ok(path=str(directory))
        except Exception as exc:
            return _error(exc)

    def list_config_backups(self) -> dict[str, Any]:
        try:
            return _ok(backups=profiles.list_backups())
        except Exception as exc:
            return _error(exc)

    def read_config_backup(self, name: str) -> dict[str, Any]:
        try:
            return _ok(**profiles.read_backup(str(name)))
        except Exception as exc:
            return _error(exc)

    def restore_config_backup(self, name: str) -> dict[str, Any]:
        try:
            result = profiles.restore_backup(str(name))
            return _ok(message=f"已還原至 {result['target']}", **result)
        except Exception as exc:
            return _error(exc)

    def select_folder(self, path: str = "") -> dict[str, Any]:
        """Desktop-mode folder picker (web mode uses browse_directories)."""
        try:
            window = self._window_getter()
            if window is None:
                raise RuntimeError("視窗尚未初始化")
            try:
                import webview
            except ImportError as exc:
                raise RuntimeError("pywebview 尚未安裝") from exc
            start = str(path).strip() or str(self._ssh_dir_or_home())
            result = window.create_file_dialog(
                _folder_dialog_type(webview),
                directory=start,
                allow_multiple=False,
            )
            if not result:
                return _ok(cancelled=True, path="")
            selected = result[0] if isinstance(result, (tuple, list)) else result
            return _ok(path=str(selected))
        except Exception as exc:
            return _error(exc, cancelled=True)

    def _ssh_dir_or_home(self):
        try:
            return get_ssh_dir()
        except Exception:
            from pathlib import Path

            return Path.home()

    def _profile_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Translate the dialog payload into git-key fields for profiles.py.

        core.sshCommand comes either from a picked SSH key name ("ssh_key")
        or a raw custom command ("ssh_command"); neither present = inherit.
        """
        converted: dict[str, Any] = {
            "user.name": _blank_to_none(fields.get("user.name")),
            "user.email": _blank_to_none(fields.get("user.email")),
            "user.signingkey": _blank_to_none(fields.get("user.signingkey")),
            "commit.gpgsign": _blank_to_none(fields.get("commit.gpgsign")),
            "tag.gpgSign": _blank_to_none(fields.get("tag.gpgSign")),
        }
        ssh_key = _blank_to_none(fields.get("ssh_key"))
        ssh_command = _blank_to_none(fields.get("ssh_command"))
        if ssh_key:
            converted["core.sshCommand"] = profiles.build_ssh_command(self._ssh_private_path(ssh_key))
        elif ssh_command:
            converted["core.sshCommand"] = ssh_command
        else:
            converted["core.sshCommand"] = None
        return converted

    def _ssh_private_path(self, name: str) -> str:
        for key in discover_ssh_keys(get_ssh_dir()):
            if key.name == name:
                if not key.has_private_key:
                    raise RuntimeError(f"SSH Key「{name}」沒有 Private Key，無法用於 core.sshCommand")
                return str(key.private_path)
        raise RuntimeError(f"找不到 SSH Key：{name}")


# 掃描 Git Repo 時略過的系統／依賴目錄（與 Git Ref Manager Browse-Filesystem 一致）
_SCAN_SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information", "Windows",
                   "Program Files", "Program Files (x86)", "ProgramData", "node_modules"}


def _scan_repos(path: str, depth: int = 2, limit: int = 50) -> list[dict[str, str]]:
    """在 path 底下以 DFS 找 .git 目錄（深度 depth、最多 limit 個）。"""
    start = Path(str(path or "")).expanduser().resolve()
    if not start.is_dir():
        raise NotADirectoryError(f"找不到資料夾：{start}")
    found: list[dict[str, str]] = []
    stack: list[tuple[Path, int]] = [(start, 0)]
    while stack and len(found) < limit:
        current, level = stack.pop()
        try:
            children = sorted((p for p in current.iterdir() if p.is_dir()),
                              key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in children:
            if len(found) >= limit:
                break
            if child.name in _SCAN_SKIP_DIRS:
                continue
            try:
                if (child / ".git").exists():
                    found.append({"path": str(child), "name": child.name})
            except OSError:
                continue
            if level < depth:
                stack.append((child, level + 1))
    return found


def _list_roots() -> list[dict[str, str]]:
    import os
    import string

    if os.name == "nt":
        roots = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.isdir(drive):
                roots.append({"name": drive, "path": drive})
        return roots
    home = str(Path.home())
    return [{"name": "/", "path": "/"}, {"name": home, "path": home}]
