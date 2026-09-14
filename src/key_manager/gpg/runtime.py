from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import threading

from key_manager.command import CommandResult, run_command
from .git_gpg import FIXED_GIT_BASH, find_git_bash


_GPG_PROCESS_LOCK = threading.RLock()
Runner = Callable[..., CommandResult]


def _runner_or_default(runner: Runner | None) -> Runner:
    return run_command if runner is None else runner


def run_git_gpg(
    args: Sequence[str],
    *,
    timeout: float = 60.0,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    bash_path=None,
    runner: Runner | None = None,
) -> CommandResult:
    """Run gpg inside a Git Bash login shell.

    Arguments are forwarded through Bash positional parameters instead of
    interpolated into the command string. This preserves the same Git Bash
    environment the user relies on while avoiding shell quoting/injection
    problems. It deliberately leaves GnuPG storage/environment to Git Bash.
    """
    runner = _runner_or_default(runner)
    with _GPG_PROCESS_LOCK:
        bash = bash_path or find_git_bash()
        if bash is None:
            return CommandResult(127, "", f"找不到 Git Bash：{FIXED_GIT_BASH}")
        command = [
            str(bash),
            "-lc",
            'exec gpg "$@"',
            "key-manager",
            *list(args),
        ]
        if input_text is None:
            return runner(command, timeout=timeout, env=env)
        return runner(command, timeout=timeout, env=env, input_text=input_text)
