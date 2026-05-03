"""Write confirmation token management for Sunsynk."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class WriteConfirmation:
    """A confirmation token for Tier 1/3 write operations."""

    token: str = field(default_factory=lambda: str(uuid.uuid4()))
    service: str = ""
    params: dict = field(default_factory=dict)
    expires_at: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(seconds=60)
    )

    def is_valid(self) -> bool:
        """Return True if the token has not expired."""
        return datetime.now() < self.expires_at

    def is_expired(self) -> bool:
        """Return True if the token has expired."""
        return not self.is_valid()
