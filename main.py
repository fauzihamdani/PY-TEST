import logging
from datetime import time
from typing import Any

from executor import registry
from repository import InMemoryRepository
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def add_task_from_dict(repo: InMemoryRepository, cfg: dict[str, Any]):
    return repo.add_task(
        cfg["user"],
        time.fromisoformat(cfg["run_at"]),  # "HH:MM" (UTC)
        cfg["action"],
        cfg["target"],
        cfg.get("params"),
    )


task_configs = [
    {
        "user": "alice",
        "run_at": "00:00",
        "action": "sync",
        "target": "/data/x",
        "params": {"mode": "incremental"},
    },
    {
        "user": "alice",
        "run_at": "00:00",
        "action": "sync",
        "target": "/data/y",
        "params": {"mode": "full"},
    },
    {
        "user": "alice",
        "run_at": "00:00",
        "action": "delete",
        "target": "/tmp/z",
        "params": {"recursive": True},
    },
    {
        "user": "bob",
        "run_at": "00:00",
        "action": "backup",
        "target": "/srv/y",
        "params": {"compress": True},
    },
]

repo = InMemoryRepository()
repo.add_user("alice", 3)
repo.add_user("bob", 5)
for cfg in task_configs:
    add_task_from_dict(repo, cfg)

if __name__ == "__main__":
    Scheduler(repo, registry).run_forever()
