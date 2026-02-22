"""Cron-friendly runner for watcher tasks."""

from __future__ import annotations

import importlib
import logging
import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from watcher.store import store as watcher_store
from watcher.tasks import TASKS

log = logging.getLogger(__name__)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_due(task: dict, last_run: str | None) -> bool:
    interval_seconds = task.get("interval_seconds")
    if not interval_seconds:
        return True
    last_dt = _parse_time(last_run)
    if not last_dt:
        return True
    now = datetime.now(timezone.utc)
    return (now - last_dt).total_seconds() >= float(interval_seconds)


def _load_task_runner(task: dict) -> Callable[[dict], dict]:
    script = task.get("script") or ""
    if not script:
        raise ValueError("Task missing script")

    if script.endswith(".py"):
        script_path = Path(script)
        if not script_path.exists():
            raise FileNotFoundError(f"Task script not found: {script}")
        module_globals = runpy.run_path(str(script_path))
        runner = module_globals.get("run")
    else:
        module = importlib.import_module(script)
        runner = getattr(module, "run", None)

    if not callable(runner):
        raise ValueError(f"Task script missing run(task) function: {script}")
    return runner


def run_once() -> None:
    for task in TASKS:
        if not task.get("enabled", False):
            continue

        task_id = task.get("id") or ""
        if not task_id:
            log.warning("Skipping task without id")
            continue

        last_run = watcher_store.get_last_run(task_id)
        if not _is_due(task, last_run):
            continue

        try:
            runner = _load_task_runner(task)
            result = runner(task)
            watcher_store.set_last_run(task_id)
            log.info("Task %s completed: %s", task_id, result)
        except Exception as exc:
            log.exception("Task %s failed: %s", task_id, exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_once()


if __name__ == "__main__":
    main()
