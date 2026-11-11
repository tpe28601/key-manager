"""Minimal OpenSSH client config parser (SPEC-1.2 section 4.5 scope).

Understands Host / HostName / IdentityFile, one level of Include, and marks
Match blocks as skipped. Everything else in the file is ignored on purpose.
"""

from __future__ import annotations

import glob as glob_module
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SSHHostBlock:
    pattern: str
    patterns: tuple[str, ...]
    hostname: str
    identity_files: tuple[str, ...]
    source: str


@dataclass
class SSHConfigData:
    hosts: list[SSHHostBlock] = field(default_factory=list)
    unresolved_includes: list[str] = field(default_factory=list)
    match_blocks: int = 0


def expand_identity_path(value: str, ssh_dir: Path) -> str:
    """Expand ``~`` and ``%d`` (the ssh directory) inside an IdentityFile value."""
    text = str(value).strip().strip('"').strip("'")
    if "%d" in text:
        text = text.replace("%d", str(ssh_dir))
    return os.path.expanduser(text)


def _strip_comment(line: str) -> str:
    # ssh_config comments start at '#' at line start or after whitespace.
    out: list[str] = []
    previous = ""
    for char in line:
        if char == "#" and (not out or previous.isspace()):
            break
        out.append(char)
        previous = char
    return "".join(out).strip()


def _tokenize(line: str) -> tuple[str, str] | None:
    """Return (keyword, value) for ``Keyword value`` or ``Keyword=value``."""
    if not line:
        return None
    keyword, separator, value = line.partition(" ")
    if not separator:
        keyword, separator, value = line.partition("=")
        if not separator:
            return keyword, ""
    return keyword, value.strip()


def _parse_lines(lines: list[str], source: str) -> tuple[list[tuple[list[str], str, list[str], str]], int]:
    """Parse one file's lines into (host blocks, match block count).

    A block is (patterns, hostname, identity_files, source).
    """
    blocks: list[tuple[list[str], str, list[str], str]] = []
    match_blocks = 0
    patterns: list[str] | None = None
    hostname = ""
    identities: list[str] = []
    in_match = False

    def flush() -> None:
        nonlocal patterns, hostname, identities
        if patterns:
            blocks.append((patterns, hostname, identities, source))
        patterns, hostname, identities = None, "", []

    for raw_line in lines:
        line = _strip_comment(raw_line)
        if not line:
            continue
        token = _tokenize(line)
        if token is None:
            continue
        keyword, value = token
        lowered = keyword.lower()
        if lowered == "host":
            flush()
            in_match = False
            patterns = [item.strip('"') for item in value.split() if item.strip('"')]
        elif lowered == "match":
            flush()
            in_match = True
            match_blocks += 1
        elif in_match or patterns is None:
            # Inside a Match block, or keywords before the first Host: out of scope.
            continue
        elif lowered == "hostname":
            hostname = value.strip('"')
        elif lowered == "identityfile":
            if value:
                identities.append(value.strip('"'))
    flush()
    return blocks, match_blocks


def parse_ssh_config(path: Path, _depth: int = 0) -> SSHConfigData:
    """Parse an ssh config file, following Include directives one level deep."""
    data = SSHConfigData()
    path = Path(path)
    if not path.is_file():
        return data
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return data

    blocks, match_blocks = _parse_lines(lines, str(path))
    data.match_blocks += match_blocks

    includes: list[str] = []
    host_blocks: list[tuple[list[str], str, list[str], str]] = []
    # Include lines were not consumed by _parse_lines (unknown keywords are
    # ignored), so scan again for them to keep block parsing simple.
    for raw_line in lines:
        line = _strip_comment(raw_line)
        token = _tokenize(line)
        if token and token[0].lower() == "include":
            includes.extend(token[1].split())

    for pattern, hostname, identities, source in blocks:
        for pattern_item in pattern:
            data.hosts.append(
                SSHHostBlock(
                    pattern=pattern_item,
                    patterns=tuple(pattern),
                    hostname=hostname,
                    identity_files=tuple(identities),
                    source=source,
                )
            )

    if _depth >= 1:
        if includes:
            data.unresolved_includes.append("有 Include 未解析")
        return data

    for include_value in includes:
        expanded = os.path.expanduser(include_value.strip().strip('"'))
        candidate = Path(expanded)
        if not candidate.is_absolute():
            candidate = path.parent / expanded
        matches = sorted(glob_module.glob(str(candidate)))
        if not matches:
            data.unresolved_includes.append(include_value)
            continue
        for matched in matches:
            included = parse_ssh_config(Path(matched), _depth + 1)
            data.hosts.extend(included.hosts)
            data.unresolved_includes.extend(included.unresolved_includes)
            data.match_blocks += included.match_blocks
    return data
