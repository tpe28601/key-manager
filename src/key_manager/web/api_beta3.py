from __future__ import annotations

from pathlib import Path
from typing import Any

from key_manager.settings import get_ssh_dir, reset_ssh_dir, set_ssh_dir
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
