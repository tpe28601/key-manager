from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SSHKeyInfo:
    name: str
    public_path: Path
    private_path: Path
    algorithm: str
    fingerprint: str
    comment: str
    has_private_key: bool
