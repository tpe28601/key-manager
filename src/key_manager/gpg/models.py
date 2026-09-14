from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GPGKeyInfo:
    fingerprint: str
    user_id: str
    name: str
    email: str
    algorithm: str
    created_at: datetime
    expires_at: datetime | None
    has_secret_key: bool
