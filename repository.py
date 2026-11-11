import itertools
import threading
from collections import defaultdict
from datetime import date, datetime, time
from typing import Any, Protocol

from errors import UnknownUserError
from models import Task, User


class Repository(Protocol):
    def add_user(self, name: str, daily_quota: int) -> None: ...
    def add_task(
        self,
        user: str,
        run_at: time,
        action: str,
        target: str,
        params: dict[str, Any] | None = None,
    ) -> Task: ...
    def due_tasks(self, now: datetime) -> list[Task]: ...
    def claim(self, task_id: int, day: date) -> bool: ...
    def consume_quota(self, user: str, day: date) -> bool: ...
    def refund_quota(self, user: str, day: date) -> None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users: dict[str, User] = {}
        self._tasks: dict[int, Task] = {}
        self._claimed: set[tuple[int, date]] = set()
        self._used: dict[tuple[str, date], int] = defaultdict(int)
        self._seq = itertools.count(1)

    def add_user(self, name: str, daily_quota: int) -> None:
        with self._lock:
            self._users[name] = User(name, daily_quota)

    def add_task(
        self,
        user: str,
        run_at: time,
        action: str,
        target: str,
        params: dict[str, Any] | None = None,
    ) -> Task:
        with self._lock:
            task = Task(
                next(self._seq), user, run_at, action, target, dict(params or {})
            )
            self._tasks[task.id] = task
            return task

    def due_tasks(self, now: datetime) -> list[Task]:
        day, t = now.date(), now.time()
        with self._lock:
            due = [
                x
                for x in self._tasks.values()
                if x.run_at <= t and (x.id, day) not in self._claimed
            ]
        return sorted(due, key=lambda x: (x.run_at, x.id))

    def claim(self, task_id: int, day: date) -> bool:
        with self._lock:
            key = (task_id, day)
            if key in self._claimed:
                return False
            self._claimed.add(key)
            return True

    def consume_quota(self, user: str, day: date) -> bool:
        with self._lock:
            u = self._users.get(user)
            if u is None:
                raise UnknownUserError(user)
            if self._used[(user, day)] >= u.daily_quota:
                return False
            self._used[(user, day)] += 1
            return True

    def refund_quota(self, user: str, day: date) -> None:
        with self._lock:
            key = (user, day)
            self._used[key] = max(0, self._used[key] - 1)
