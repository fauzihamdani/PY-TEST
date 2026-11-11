import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timezone
from time import monotonic
from typing import Callable

from errors import UnknownUserError
from executor import ActionRegistry
from models import Task
from repository import Repository

log = logging.getLogger("scheduler")


class Scheduler:
    def __init__(
        self,
        repo: Repository,
        executor: ActionRegistry,
        workers: int = 8,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repo = repo
        self._executor = executor
        self._pool = ThreadPoolExecutor(max_workers=workers)
        self._clock = clock
        self._stop = threading.Event()

    def tick(self, now: datetime | None = None) -> None:
        now = now or self._clock()
        day = now.date()
        futures = []
        for task in self._repo.due_tasks(now):
            if not self._repo.claim(task.id, day):
                continue
            try:
                allowed = self._repo.consume_quota(task.user, day)
            except UnknownUserError:
                log.error("unknown user: %s", task.user)
                continue
            if not allowed:
                log.warning("%s exceeded quota, skip task %s", task.user, task.id)
                continue
            futures.append(self._pool.submit(self._run, task, day))
        wait(futures)

    def _run(self, task: Task, day: date) -> None:
        log.info(
            "start task=%s user=%s action=%s target=%s params=%s",
            task.id,
            task.user,
            task.action,
            task.target,
            task.params,
        )
        started = monotonic()
        try:
            self._executor.execute(task)
            log.info("done task=%s in %.3fs", task.id, monotonic() - started)
        except Exception:
            self._repo.refund_quota(task.user, day)
            log.exception("failed task=%s after %.3fs", task.id, monotonic() - started)

    def run_forever(self, interval: float = 30.0) -> None:
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(interval)

    def stop(self) -> None:
        self._stop.set()
        self._pool.shutdown(wait=True)
