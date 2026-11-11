from dataclasses import dataclass, field
from datetime import time
from typing import Any


@dataclass(frozen=True)
class User:
    name: str
    daily_quota: int


@dataclass(frozen=True)
class Task:
    id: int
    user: str
    run_at: time
    action: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)
