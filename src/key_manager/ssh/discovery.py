from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from .models import SSHKeyInfo


def _fingerprint(blob_text: str) -> str:
    padded = blob_text + "=" * (-len(blob_text) % 4)
    blob = base64.b64decode(padded, validate=True)
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{digest}"


def parse_public_key(path: Path) -> SSHKeyInfo:
    line = path.read_text(encoding="utf-8").strip()
    parts = line.split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError("Malformed OpenSSH public key")
    algorithm, blob_text = parts[:2]
    if not algorithm.startswith(("ssh-", "ecdsa-", "sk-")):
        raise ValueError("Unsupported OpenSSH public key format")
    comment = parts[2] if len(parts) == 3 else ""
    private_path = path.with_suffix("")
    return SSHKeyInfo(
        name=private_path.name,
        public_path=path,
        private_path=private_path,
        algorithm=algorithm,
        fingerprint=_fingerprint(blob_text),
        comment=comment,
        has_private_key=private_path.exists(),
    )


def discover_ssh_keys(ssh_dir: Path) -> list[SSHKeyInfo]:
    if not ssh_dir.exists() or not ssh_dir.is_dir():
        return []
    keys: list[SSHKeyInfo] = []
    for public_path in sorted(ssh_dir.glob("*.pub")):
        try:
            keys.append(parse_public_key(public_path))
        except (OSError, UnicodeError, ValueError, base64.binascii.Error):
            continue
    return keys
