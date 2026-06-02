"""APScheduler integration for recurring pipeline execution.

Provides cron-based scheduling for pipelines defined in pipelines.yaml.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None  # type: ignore[assignment,misc]
    CronTrigger = None  # type: ignore[assignment,misc]


_scheduler: Any = None


def get_scheduler() -> Any:
    """Get or create the global APScheduler instance."""
    global _scheduler
    if _scheduler is None:
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not installed. Run: pip install apscheduler")
            return None
        _scheduler = AsyncIOScheduler()
    return _scheduler


def schedule_pipeline(pipeline_key: str, cron_expression: str, **kwargs: Any) -> str | None:
    """Schedule a pipeline to run on a cron schedule.

    Args:
        pipeline_key: Pipeline key from pipelines.yaml.
        cron_expression: Cron expression (e.g., "0 9 * * *" for daily at 9 AM).
        **kwargs: Additional arguments passed to run_pipeline.

    Returns:
        Job ID string, or None if scheduler is unavailable.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return None

    parts = cron_expression.split()
    if len(parts) != 5:
        logger.error("Invalid cron expression: {}", cron_expression)
        return None

    minute, hour, day, month, day_of_week = parts

    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
    )

    async def _run():
        from app.pipelines.engine import run_pipeline

        logger.info("Scheduled pipeline '{}' triggered", pipeline_key)
        try:
            await run_pipeline(pipeline_key=pipeline_key, **kwargs)
        except Exception as e:
            logger.error("Scheduled pipeline '{}' failed: {}", pipeline_key, e)

    job = scheduler.add_job(
        _run,
        trigger=trigger,
        id=f"pipeline_{pipeline_key}",
        name=f"Pipeline: {pipeline_key}",
        replace_existing=True,
    )

    logger.info(
        "Scheduled pipeline '{}' with cron '{}' (job_id={})",
        pipeline_key,
        cron_expression,
        job.id,
    )
    return job.id


def start_scheduler() -> None:
    """Start the scheduler and register all pipelines with schedule configs."""
    scheduler = get_scheduler()
    if scheduler is None:
        return

    from app.pipelines.engine import load_pipeline_configs

    configs = load_pipeline_configs()
    for key, config in configs.items():
        if config.schedule:
            schedule_pipeline(key, config.schedule)

    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started with {} jobs", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    scheduler = get_scheduler()
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def get_scheduled_jobs() -> list[dict[str, Any]]:
    """Return info about all scheduled jobs."""
    scheduler = get_scheduler()
    if scheduler is None:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )
    return jobs
