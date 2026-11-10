from __future__ import annotations

from pathlib import Path
from typing import Any

from key_manager.settings import get_ssh_dir, get_theme, reset_ssh_dir, set_ssh_dir, set_theme
from key_manager.gpg.export import armor_public_key
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

    def browse_directories(self, path: str = "") -> dict[str, Any]:
        """列出資料夾，給瀏覽器內的資料夾選擇器用。path 空白時回傳磁碟機 / 根目錄。"""
        try:
            raw = str(path or "").strip()
            if not raw:
                roots = _list_roots()
                return _ok(path="", parent=None, dirs=roots, roots=roots)
            current = Path(raw).expanduser()
            if not current.is_absolute():
                raise ValueError("請輸入完整路徑")
            current = current.resolve()
            if not current.is_dir():
                raise NotADirectoryError(f"找不到資料夾：{current}")
            dirs: list[dict[str, str]] = []
            try:
                entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
            except PermissionError as exc:
                raise PermissionError(f"沒有權限讀取：{current}") from exc
            for entry in entries:
                try:
                    if entry.is_dir():
                        dirs.append({"name": entry.name, "path": str(entry)})
                except OSError:
                    continue
            parent = None if current.parent == current else str(current.parent)
            return _ok(path=str(current), parent=parent, dirs=dirs, roots=_list_roots())
        except Exception as exc:
            return _error(exc, path=str(path or ""), parent=None, dirs=[])

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
