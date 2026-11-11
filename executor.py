import logging
from pathlib import PurePosixPath
from typing import Any, Callable

from errors import ValidationError
from models import Task

log = logging.getLogger("executor")
Handler = Callable[[str, str, dict[str, Any]], None]


class ActionRegistry:
    def __init__(self, allowed_roots: tuple[str, ...]) -> None:
        self._handlers: dict[str, Handler] = {}
        self._roots = tuple(PurePosixPath(r) for r in allowed_roots)

    def register(self, action: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self._handlers[action] = fn
            return fn

        return deco

    def _validate(self, target: str) -> str:
        p = PurePosixPath(target)
        if not p.is_absolute() or ".." in p.parts:
            raise ValidationError(f"invalid target: {target}")
        if not any(p.is_relative_to(r) for r in self._roots):
            raise ValidationError(f"target outside allowed roots: {target}")
        return str(p)

    def execute(self, task: Task) -> None:
        handler = self._handlers.get(task.action)
        if handler is None:
            raise ValidationError(f"unknown action: {task.action}")
        handler(task.user, self._validate(task.target), task.params)


registry = ActionRegistry(allowed_roots=("/data", "/srv", "/tmp"))


@registry.register("sync")
def sync(user: str, target: str, params: dict[str, Any]) -> None:
    mode = params.get("mode", "full")
    log.info("sync %s for %s (mode=%s)", target, user, mode)


@registry.register("backup")
def backup(user: str, target: str, params: dict[str, Any]) -> None:
    compress = params.get("compress", False)
    log.info("backup %s for %s (compress=%s)", target, user, compress)


@registry.register("delete")
def delete(user: str, target: str, params: dict[str, Any]) -> None:
    recursive = params.get("recursive", False)
    log.info("delete %s for %s (recursive=%s)", target, user, recursive)
