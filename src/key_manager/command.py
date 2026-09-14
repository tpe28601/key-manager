from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os
import shutil
import subprocess


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _is_windows() -> bool:
    return os.name == "nt"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _window_options() -> dict[str, object]:
    if not _is_windows():
        return {}
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    options: dict[str, object] = {"creationflags": create_no_window}
    startupinfo_type = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_type is not None:
        startupinfo = startupinfo_type()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        options["startupinfo"] = startupinfo
    return options


def run_command(
    args: Sequence[str],
    timeout: float = 30.0,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
) -> CommandResult:
    completed = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
        env=None if env is None else dict(env),
        shell=False,
        check=False,
        **_window_options(),
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)
