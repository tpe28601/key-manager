from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parseaddr
from string import hexdigits

from key_manager.command import run_command
from .git_gpg import find_git_bash
from .models import GPGKeyInfo
from .runtime import run_git_gpg


_ALGO_NAMES = {
    "1": "RSA",
    "16": "ElGamal",
    "17": "DSA",
    "18": "ECDH",
    "19": "ECDSA",
    "22": "EdDSA",
}


def _percent_unescape(value: str) -> str:
    out = bytearray()
    i = 0
    while i < len(value):
        if i + 2 < len(value) and value[i] == "%" and value[i + 1] in hexdigits and value[i + 2] in hexdigits:
            out.append(int(value[i + 1 : i + 3], 16))
            i += 3
            continue
        out.extend(value[i].encode("utf-8"))
        i += 1
    return out.decode("utf-8", errors="replace")


def _timestamp(value: str) -> datetime:
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _optional_timestamp(value: str) -> datetime | None:
    if not value or value == "0":
        return None
    return _timestamp(value)


def _algorithm(fields: list[str]) -> str:
    lowered = {field.lower() for field in fields if field}
    for candidate in ("ed25519", "cv25519", "nistp256", "nistp384", "nistp521"):
        if candidate in lowered:
            return candidate
    return _ALGO_NAMES.get(fields[3] if len(fields) > 3 else "", fields[3] if len(fields) > 3 else "Unknown")


def _primary_secret_fingerprints(text: str) -> set[str]:
    fingerprints: set[str] = set()
    awaiting_fpr = False
    for raw in text.splitlines():
        fields = raw.split(":")
        record = fields[0] if fields else ""
        if record == "sec":
            awaiting_fpr = True
        elif record in {"ssb", "pub", "sub"}:
            awaiting_fpr = False
        elif record == "fpr" and awaiting_fpr and len(fields) > 9 and fields[9]:
            fingerprints.add(fields[9])
            awaiting_fpr = False
    return fingerprints


def parse_gpg_colons(text: str, secret_fingerprints: set[str] | None = None) -> list[GPGKeyInfo]:
    secret_fingerprints = secret_fingerprints or set()
    keys: list[GPGKeyInfo] = []
    current: dict[str, object] | None = None

    def finalize() -> None:
        nonlocal current
        if not current:
            return
        fingerprint = str(current.get("fingerprint", ""))
        if not fingerprint:
            current = None
            return
        user_id = str(current.get("user_id", ""))
        parsed_name, parsed_email = parseaddr(user_id)
        keys.append(
            GPGKeyInfo(
                fingerprint=fingerprint,
                user_id=user_id,
                name=parsed_name or user_id,
                email=parsed_email,
                algorithm=str(current["algorithm"]),
                created_at=current["created_at"],  # type: ignore[arg-type]
                expires_at=current["expires_at"],  # type: ignore[arg-type]
                has_secret_key=fingerprint in secret_fingerprints,
            )
        )
        current = None

    for raw in text.splitlines():
        if not raw:
            continue
        fields = raw.split(":")
        record = fields[0]
        if record in {"pub", "sec"}:
            finalize()
            if len(fields) <= 6 or not fields[5]:
                continue
            current = {
                "algorithm": _algorithm(fields),
                "created_at": _timestamp(fields[5]),
                "expires_at": _optional_timestamp(fields[6]),
                "fingerprint": "",
                "user_id": "",
            }
        elif current is not None and record == "fpr" and not current.get("fingerprint"):
            if len(fields) > 9:
                current["fingerprint"] = fields[9]
        elif current is not None and record == "uid" and not current.get("user_id"):
            if len(fields) > 9:
                current["user_id"] = _percent_unescape(fields[9])
    finalize()
    return keys


def discover_gpg_keys() -> list[GPGKeyInfo]:
    if find_git_bash() is None:
        return []
    result = run_git_gpg(
        ["--batch", "--with-colons", "--fingerprint", "--keyid-format", "LONG", "--list-secret-keys"],
        runner=run_command,
        timeout=60.0,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "GPG secret key listing failed")
    secret_fingerprints = _primary_secret_fingerprints(result.stdout)
    return parse_gpg_colons(result.stdout, secret_fingerprints)
