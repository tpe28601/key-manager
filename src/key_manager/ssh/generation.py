from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Literal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa


_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_key_filename(name: str) -> str:
    value = name.strip()
    if not value or value in {".", ".."} or not _SAFE_FILENAME.fullmatch(value):
        raise ValueError("SSH key filename may contain only letters, numbers, dot, underscore, and hyphen")
    return value


def _single_line_comment(comment: str) -> str:
    return " ".join(comment.replace("\r", " ").replace("\n", " ").split())


def _ensure_inside(directory: Path, target: Path) -> None:
    if target.parent.resolve() != directory.resolve():
        raise ValueError("SSH key path escapes the SSH directory")


def generate_ssh_key(
    ssh_dir: Path,
    filename: str,
    algorithm: Literal["ed25519", "rsa4096"],
    comment: str,
    passphrase: str,
) -> tuple[Path, Path]:
    filename = validate_key_filename(filename)
    ssh_dir = ssh_dir.expanduser()
    ssh_dir.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            ssh_dir.chmod(0o700)
        except OSError:
            pass

    private_path = ssh_dir / filename
    public_path = ssh_dir / f"{filename}.pub"
    _ensure_inside(ssh_dir, private_path)
    _ensure_inside(ssh_dir, public_path)

    if private_path.exists() or public_path.exists():
        raise FileExistsError(f"SSH key target already exists: {filename}")

    if algorithm == "ed25519":
        private_key = ed25519.Ed25519PrivateKey.generate()
    elif algorithm == "rsa4096":
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    else:
        raise ValueError(f"Unsupported SSH key algorithm: {algorithm}")

    encryption = (
        serialization.BestAvailableEncryption(passphrase.encode("utf-8"))
        if passphrase
        else serialization.NoEncryption()
    )
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=encryption,
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    clean_comment = _single_line_comment(comment)
    public_line = public_bytes + (b" " + clean_comment.encode("utf-8") if clean_comment else b"") + b"\n"

    private_created = False
    try:
        with private_path.open("xb") as private_file:
            private_file.write(private_bytes)
        private_created = True
        if os.name != "nt":
            private_path.chmod(0o600)
        with public_path.open("xb") as public_file:
            public_file.write(public_line)
    except Exception:
        if private_created and not public_path.exists():
            try:
                private_path.unlink()
            except OSError:
                pass
        raise

    return private_path, public_path
