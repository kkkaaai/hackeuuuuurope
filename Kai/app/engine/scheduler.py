"""Pipeline scheduler — runs cron/interval pipelines on a recurring schedule."""

from __future__ import annotations

import json
import logging
import re

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_db

logger = logging.getLogger("agentflow.scheduler")

# Maximum seconds a job can be late and still execute (APScheduler misfire tolerance).
MISFIRE_GRACE_TIME_SECONDS = 30

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    _scheduler = None


async def _execute_pipeline_job(pipeline_id: str) -> None:
    """Job callback — re-runs a pipeline by ID."""
    # Import here to avoid circular imports
    from app.api.dependencies import get_registry
    from app.engine.runner import PipelineRunner
    from app.memory.store import memory_store
    from app.models.pipeline import Pipeline

    logger.info("Scheduled execution of pipeline %s", pipeline_id)

    with get_db() as conn:
        row = conn.execute(
            "SELECT definition FROM pipelines WHERE id = ?", (pipeline_id,)
        ).fetchone()

    if row is None:
        logger.warning("Pipeline %s not found — removing scheduled job", pipeline_id)
        remove_schedule(pipeline_id)
        return

    pipeline = Pipeline(**json.loads(row["definition"]))
    registry = get_registry()
    runner = PipelineRunner(registry=registry, memory=memory_store)
    result = await runner.run(pipeline)

    with get_db() as conn:
        conn.execute(
            "UPDATE pipelines SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (result.status.value, pipeline_id),
        )
        conn.commit()

    logger.info(
        "Scheduled run of %s finished: %s", pipeline_id, result.status.value
    )


def _parse_interval_seconds(schedule: str | None) -> int | None:
    """Parse interval patterns like '*/50 * * * * *' (every 50s) or plain seconds."""
    if not schedule:
        return None

    # Check for a pure number (seconds)
    try:
        return int(schedule)
    except ValueError:
        pass

    # Check for second-level cron: */N * * * * * (6-field with seconds)
    match = re.match(r"^\*/(\d+)\s+\*\s+\*\s+\*\s+\*\s+\*$", schedule.strip())
    if match:
        return int(match.group(1))

    return None


def schedule_pipeline(
    pipeline_id: str,
    schedule: str | None,
    interval_seconds: int | None = None,
) -> bool:
    """Register a pipeline for recurring execution.

    Trigger resolution priority:
      1. Explicit ``interval_seconds`` parameter (takes precedence)
      2. Interval parsed from ``schedule`` string (e.g. "60" or "*/30 * * * * *")
      3. Standard 5-field cron expression from ``schedule`` (e.g. "0 9 * * MON-FRI")

    Returns True if scheduled successfully, False if schedule couldn't be parsed.
    """
    scheduler = get_scheduler()
    job_id = f"pipeline_{pipeline_id}"

    # Remove existing job if any
    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()

    # Determine trigger type
    seconds = interval_seconds or _parse_interval_seconds(schedule)
    if seconds is not None:
        trigger = IntervalTrigger(seconds=seconds)
        logger.info("Scheduling pipeline %s every %d seconds", pipeline_id, seconds)
    elif schedule:
        try:
            trigger = CronTrigger.from_crontab(schedule)
            logger.info("Scheduling pipeline %s with cron: %s", pipeline_id, schedule)
        except ValueError:
            logger.error("Invalid cron expression for pipeline %s: %s", pipeline_id, schedule)
            return False
    else:
        logger.warning("No schedule provided for pipeline %s", pipeline_id)
        return False

    scheduler.add_job(
        _execute_pipeline_job,
        trigger=trigger,
        args=[pipeline_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=MISFIRE_GRACE_TIME_SECONDS,
    )
    return True


def remove_schedule(pipeline_id: str) -> None:
    """Remove a scheduled pipeline job."""
    scheduler = get_scheduler()
    job_id = f"pipeline_{pipeline_id}"
    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()
        logger.info("Removed schedule for pipeline %s", pipeline_id)


def list_scheduled() -> list[dict]:
    """List all scheduled pipeline jobs."""
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "job_id": job.id,
            "pipeline_id": job.args[0] if job.args else None,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return jobs
