from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform

from key_manager.settings import get_ssh_dir


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    is_wsl: bool
    home: Path
    ssh_dir: Path


def detect_platform() -> PlatformInfo:
    system = platform.system()
    release = platform.release().lower()
    is_wsl = system == "Linux" and (
        "microsoft" in release or bool(os.environ.get("WSL_DISTRO_NAME"))
    )
    home = Path.home()
    return PlatformInfo(system=system, is_wsl=is_wsl, home=home, ssh_dir=get_ssh_dir())
