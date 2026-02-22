"""Poll Google Contacts state and trigger proactive actions."""

from watcher.engine import run_watch


def run(task: dict) -> dict:
    return run_watch(task)
