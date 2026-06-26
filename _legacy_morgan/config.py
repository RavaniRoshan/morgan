"""Morgan config module — settings, trust modes, policy."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("morgan.audit")


class TrustMode(str, Enum):
    DEFAULT = "default"
    SAFE = "safe"
    FULL_ACCESS = "full_access"


def audit_log(action: str, details: dict[str, Any] | None = None) -> None:
    """Record an action to the audit log."""
    logger.info("action=%s %s", action, details or "")


class Config(BaseModel):
    workspace_dir: Path = Path(".")
    trust_mode: TrustMode = TrustMode.DEFAULT
    max_turns: int = 50
    budget_cap: float = 10.0
