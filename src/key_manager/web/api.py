from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import os
from typing import Any, Callable

from key_manager.git.config import (
    read_global_git_config,
    set_global_identity,
    set_global_signing,
)
from key_manager.git.git_for_windows import find_git_for_windows
from key_manager.gpg.discovery import discover_gpg_keys
from key_manager.gpg.deletion import delete_gpg_key
from key_manager.gpg.export import armor_public_key, export_gpg_public_key
from key_manager.gpg.generation import create_gpg_key
from key_manager.gpg.git_gpg import find_git_bash
from key_manager.metadata import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    APP_VERSION_LABEL,
)
from key_manager.platform_info import detect_platform
from key_manager.ssh.agent import (
    add_key_to_agent,
    clear_agent_identities,
    format_agent_status,
    get_agent_status,
    is_managed_agent,
    list_agent_identities,
    remove_agent_identity,
    start_managed_agent,
    stop_managed_agent,
)
from key_manager.ssh.discovery import discover_ssh_keys
from key_manager.ssh.export import export_public_key
from key_manager.ssh.generation import generate_ssh_key


WindowGetter = Callable[[], Any]


def _ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def _error(exc: Exception, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "error": str(exc) or exc.__class__.__name__, **payload}


def _iso(value):
    return value.isoformat() if value is not None else None


def _copy_to_windows_clipboard(text: str) -> None:
    """Write Unicode text to the Windows clipboard without another GUI toolkit."""
    if os.name != "nt":
        raise RuntimeError("Clipboard integration is available in the Windows build")
    import ctypes
    from ctypes import wintypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    data = (text + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise OSError("Unable to allocate clipboard memory")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise OSError("Unable to lock clipboard memory")
    ctypes.memmove(pointer, data, len(data))
    kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise OSError("Unable to open Windows clipboard")
    try:
        if not user32.EmptyClipboard():
            raise OSError("Unable to clear Windows clipboard")
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise OSError("Unable to set Windows clipboard data")
        handle = None
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)


class KeyManagerApi:
    """Small JSON-safe bridge exposed to the WebView frontend."""

    def __init__(self, window_getter: WindowGetter) -> None:
        self._window_getter = window_getter

    def get_app_info(self) -> dict[str, Any]:
        info = detect_platform()
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "version_label": APP_VERSION_LABEL,
            "author": APP_AUTHOR,
            "description": APP_DESCRIPTION,
            "ui": "pywebview",
            "system": "WSL2" if info.is_wsl else info.system,
            "home": str(info.home),
        }

    def dashboard(self) -> dict[str, Any]:
        try:
            info = detect_platform()
            ssh_keys = discover_ssh_keys(info.ssh_dir)
            agent = get_agent_status()
            gpg_keys = discover_gpg_keys() if find_git_bash() is not None else []
            git_cfg = read_global_git_config()
            return _ok(
                ssh_count=len(ssh_keys),
                agent_status=format_agent_status(agent),
                gpg_count=len(gpg_keys),
                git_installed=find_git_for_windows() is not None,
                git_name=git_cfg.name,
                git_email=git_cfg.email,
                signing_enabled=git_cfg.commit_gpgsign and git_cfg.tag_gpgsign,
                commit_signing_enabled=git_cfg.commit_gpgsign,
                tag_signing_enabled=git_cfg.tag_gpgsign,
                signing_key=git_cfg.signing_key,
            )
        except Exception as exc:
            return _error(exc)

    def list_ssh_keys(self) -> dict[str, Any]:
        try:
            info = detect_platform()
            agent = get_agent_status()
            keys = [
                {
                    "name": key.name,
                    "public_path": str(key.public_path),
                    "private_path": str(key.private_path),
                    "algorithm": key.algorithm,
                    "fingerprint": key.fingerprint,
                    "comment": key.comment,
                    "has_private_key": key.has_private_key,
                    "agent_loaded": key.fingerprint in agent.fingerprints,
                }
                for key in discover_ssh_keys(info.ssh_dir)
            ]
            return _ok(keys=keys, agent_status=format_agent_status(agent), agent_available=agent.available)
        except Exception as exc:
            return _error(exc, keys=[])

    def create_ssh_key(self, options: dict[str, Any]) -> dict[str, Any]:
        try:
            info = detect_platform()
            private_path, public_path = generate_ssh_key(
                info.ssh_dir,
                str(options.get("filename", "id_rsa")),
                str(options.get("algorithm", "rsa4096")),
                str(options.get("comment", "")),
                str(options.get("passphrase", "")),
            )
            return _ok(private_path=str(private_path), public_path=str(public_path))
        except Exception as exc:
            return _error(exc)

    def delete_ssh_key(self, name: str) -> dict[str, Any]:
        try:
            key = self._ssh_key(name)
            deleted: list[str] = []
            for path in (key.public_path, key.private_path):
                if path.exists():
                    path.unlink()
                    deleted.append(str(path))
            if not deleted:
                raise FileNotFoundError(f"找不到 SSH Key 檔案：{name}")
            return _ok(message=f"已刪除 SSH Key：{name}", deleted=deleted)
        except Exception as exc:
            return _error(exc)

    def copy_ssh_public_key(self, name: str) -> dict[str, Any]:
        try:
            key = self._ssh_key(name)
            text = key.public_path.read_text(encoding="utf-8").strip()
            _copy_to_windows_clipboard(text)
            return _ok(message=f"已複製 {key.name} 的 Public Key")
        except Exception as exc:
            return _error(exc)

    def export_ssh_public_key(self, name: str) -> dict[str, Any]:
        try:
            key = self._ssh_key(name)
            destination = self._save_path(f"{key.name}.pub", "SSH Public Key (*.pub)")
            if destination is None:
                return _ok(cancelled=True)
            if destination.exists():
                destination.unlink()
            export_public_key(key.public_path, destination)
            return _ok(path=str(destination))
        except Exception as exc:
            return _error(exc)

    def add_ssh_key_to_agent(self, name: str) -> dict[str, Any]:
        try:
            key = self._ssh_key(name)
            if not key.has_private_key:
                raise RuntimeError("找不到對應的 Private Key")
            result = add_key_to_agent(key.private_path)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH Agent 操作失敗")
            return _ok(message="已加入 SSH Agent")
        except Exception as exc:
            return _error(exc)

    def list_ssh_agent(self) -> dict[str, Any]:
        try:
            status = get_agent_status()
            if not status.available:
                return _ok(
                    available=False,
                    managed=is_managed_agent(),
                    status=format_agent_status(status),
                    identities=[],
                )
            info = detect_platform()
            local_by_fingerprint = {key.fingerprint: key.name for key in discover_ssh_keys(info.ssh_dir)}
            identities = [
                {
                    "fingerprint": identity.fingerprint,
                    "comment": identity.comment,
                    "algorithm": identity.algorithm,
                    "local_name": local_by_fingerprint.get(identity.fingerprint, ""),
                }
                for identity in list_agent_identities()
            ]
            return _ok(
                available=True,
                managed=is_managed_agent(),
                status=format_agent_status(status),
                identities=identities,
            )
        except Exception as exc:
            return _error(exc, available=False, managed=is_managed_agent(), identities=[])

    def start_ssh_agent(self) -> dict[str, Any]:
        try:
            result = start_managed_agent()
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH Agent 啟動失敗")
            return _ok(message="SSH Agent 已啟動")
        except Exception as exc:
            return _error(exc)

    def remove_ssh_agent_key(self, fingerprint: str) -> dict[str, Any]:
        try:
            result = remove_agent_identity(fingerprint)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH Agent Key 移除失敗")
            return _ok(message="已從 SSH Agent 移除 Key")
        except Exception as exc:
            return _error(exc)

    def clear_ssh_agent(self) -> dict[str, Any]:
        try:
            result = clear_agent_identities()
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH Agent 清空失敗")
            return _ok(message="SSH Agent 已清空")
        except Exception as exc:
            return _error(exc)

    def stop_ssh_agent(self) -> dict[str, Any]:
        try:
            result = stop_managed_agent()
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH Agent 停止失敗")
            return _ok(message="Key Manager 啟動的 SSH Agent 已停止")
        except Exception as exc:
            return _error(exc)

    def open_ssh_folder(self) -> dict[str, Any]:
        try:
            path = detect_platform().ssh_dir
            if os.name != "nt":
                raise RuntimeError("此功能僅支援 Windows")
            os.startfile(str(path))  # type: ignore[attr-defined]
            return _ok()
        except Exception as exc:
            return _error(exc)

    def list_gpg_keys(self) -> dict[str, Any]:
        try:
            keys = [
                {
                    "fingerprint": key.fingerprint,
                    "user_id": key.user_id,
                    "name": key.name,
                    "email": key.email,
                    "algorithm": key.algorithm,
                    "created_at": _iso(key.created_at),
                    "expires_at": _iso(key.expires_at),
                    "has_secret_key": key.has_secret_key,
                }
                for key in discover_gpg_keys()
            ]
            return _ok(keys=keys)
        except Exception as exc:
            return _error(exc, keys=[])

    def create_gpg_key(self, options: dict[str, Any]) -> dict[str, Any]:
        try:
            result = create_gpg_key(
                str(options.get("name", "")),
                str(options.get("email", "")),
                str(options.get("expire", "2y")),
                str(options.get("algorithm", "rsa4096")),
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "建立 GPG Key 失敗")
            return _ok(message="GPG Key 建立完成")
        except Exception as exc:
            return _error(exc)

    def delete_gpg_key(self, fingerprint: str) -> dict[str, Any]:
        try:
            self._require_gpg_key(fingerprint)
            result = delete_gpg_key(fingerprint)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "刪除 GPG Key 失敗")
            return _ok(message="已刪除 GPG Secret/Public Key")
        except Exception as exc:
            return _error(exc)

    def copy_gpg_public_key(self, fingerprint: str) -> dict[str, Any]:
        try:
            text = armor_public_key(fingerprint)
            _copy_to_windows_clipboard(text)
            return _ok(message="已複製 GPG Public Key")
        except Exception as exc:
            return _error(exc)

    def export_gpg_public_key(self, fingerprint: str) -> dict[str, Any]:
        try:
            self._require_gpg_key(fingerprint)
            destination = self._save_path("gpg-public-key.asc", "GPG Public Key (*.asc)")
            if destination is None:
                return _ok(cancelled=True)
            if destination.exists():
                destination.unlink()
            export_gpg_public_key(fingerprint, destination)
            return _ok(path=str(destination))
        except Exception as exc:
            return _error(exc)

    def read_git_config(self) -> dict[str, Any]:
        try:
            config = read_global_git_config()
            return _ok(config=asdict(config))
        except Exception as exc:
            return _error(exc, config={})

    def save_git_identity(self, name: str, email: str) -> dict[str, Any]:
        try:
            set_global_identity(name, email)
            return _ok(message="Git Identity 已更新")
        except Exception as exc:
            return _error(exc)

    def save_git_signing(self, fingerprint: str, enabled: bool) -> dict[str, Any]:
        try:
            set_global_signing(fingerprint, bool(enabled))
            return _ok(message="Git GPG Signing（Commit + Tag）設定已更新")
        except Exception as exc:
            return _error(exc)

    def _ssh_key(self, name: str):
        info = detect_platform()
        for key in discover_ssh_keys(info.ssh_dir):
            if key.name == name:
                return key
        raise KeyError(f"找不到 SSH Key：{name}")

    def _require_gpg_key(self, fingerprint: str) -> None:
        normalized = fingerprint.replace(" ", "").upper()
        if not any(key.fingerprint.upper() == normalized for key in discover_gpg_keys()):
            raise KeyError("找不到指定的 GPG Key")

    def _save_path(self, default_name: str, file_types: str) -> Path | None:
        window = self._window_getter()
        if window is None:
            raise RuntimeError("視窗尚未初始化")
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError("pywebview 尚未安裝") from exc
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=default_name,
            file_types=(file_types, "All files (*.*)"),
        )
        if not result:
            return None
        if isinstance(result, (tuple, list)):
            result = result[0]
        return Path(str(result))
