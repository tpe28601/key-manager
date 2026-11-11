"""Shared fixtures: a fully sandboxed git + LOCALAPPDATA environment.

Every git invocation in tests must run under these fixtures so the real
~/.gitconfig (GIT_CONFIG_GLOBAL) and real %LOCALAPPDATA% are never touched.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from key_manager.git.git_for_windows import find_git_for_windows

GIT = find_git_for_windows()
requires_git = pytest.mark.skipif(GIT is None, reason="Git for Windows is not installed")


def git_run(*args: str, cwd: Path | str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(GIT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        shell=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed ({result.returncode}): {result.stderr}")
    return result


@pytest.fixture(autouse=True)
def sandbox_local_appdata(monkeypatch, tmp_path: Path):
    """Never let any test touch the real %LOCALAPPDATA%\\KeyManager directory."""
    from key_manager import settings

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setattr(settings, "_settings_dir_override", None)


@pytest.fixture()
def git_env(monkeypatch, tmp_path: Path) -> Path:
    """Sandbox: GIT_CONFIG_GLOBAL and LOCALAPPDATA point inside tmp_path only."""
    assert GIT is not None, "Git for Windows is required for this test"
    home = tmp_path / "home"
    home.mkdir()
    global_config = home / ".gitconfig"
    global_config.write_text(
        "# user comment: keep me\n"
        "[user]\n"
        "\tname = Global Alice\n"
        "\temail = alice@example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    return tmp_path


@pytest.fixture()
def git_cli():
    return git_run
