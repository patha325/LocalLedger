from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

EventKind = Literal["agent_start", "agent_end", "tool_call", "tool_result", "error"]


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    agent: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[Event], None]
