"""APScheduler for managing snipe timing"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from .config import config
from .core.db import WatchStore
from .core.ntp import NTPSync
from .core.sniper import SniperEngine

logger = logging.getLogger(__name__)
_CURRENT_SCHEDULER: "SniperScheduler | None" = None


def _get_current_scheduler() -> "SniperScheduler":
    if _CURRENT_SCHEDULER is None:
        raise RuntimeError("SniperScheduler has not been initialized")
    return _CURRENT_SCHEDULER


def execute_snipe_job(watch_id: str):
    """APScheduler-compatible top-level job for executing a snipe."""
    asyncio.run(_get_current_scheduler()._execute_snipe_wrapper(watch_id))


def check_result_job(watch_id: str):
    """APScheduler-compatible top-level job for checking a snipe result."""
    asyncio.run(_get_current_scheduler()._check_result_wrapper(watch_id))


class SniperScheduler:
    """Scheduler for managing snipe timing with APScheduler"""

    def __init__(
        self,
        db: WatchStore,
        sniper: SniperEngine,
        ntp: NTPSync,
    ):
        """Initialize scheduler"""
        self.db = db
        self.sniper = sniper
        self.ntp = ntp

        # Setup job store
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{config.DB_PATH}")}

        # Setup executor
        executors = {"default": ThreadPoolExecutor(10)}

        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone=timezone.utc,
        )

        self.running = False
        global _CURRENT_SCHEDULER
        _CURRENT_SCHEDULER = self

    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.scheduler.start()
            self.running = True
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler already running")

    def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("Scheduler stopped")

    def schedule_watch(self, watch_id: str, end_time: str):
        """Schedule snipe for a watch

        Schedules two jobs:
        1. execute_snipe at end_time - BID_OFFSET_SECONDS
        2. check_result at end_time + RESULT_CHECK_DELAY_SECONDS

        Args:
            watch_id: Watch ID
            end_time: ISO 8601 auction end time
        """
        end_time_dt = datetime.fromisoformat(end_time)

        # Calculate snipe time (NTP-adjusted)
        snipe_time = end_time_dt - timedelta(seconds=config.BID_OFFSET_SECONDS)
        check_time = end_time_dt + timedelta(seconds=config.RESULT_CHECK_DELAY_SECONDS)

        # Schedule snipe
        snipe_job_id = f"snipe_{watch_id}"
        self.scheduler.add_job(
            func=execute_snipe_job,
            trigger=DateTrigger(run_date=snipe_time, timezone=timezone.utc),
            id=snipe_job_id,
            args=[watch_id],
            replace_existing=True,
        )

        # Schedule result check
        check_job_id = f"check_{watch_id}"
        self.scheduler.add_job(
            func=check_result_job,
            trigger=DateTrigger(run_date=check_time, timezone=timezone.utc),
            id=check_job_id,
            args=[watch_id],
            replace_existing=True,
        )

        logger.info(
            f"Scheduled snipe for watch {watch_id} at {snipe_time} "
            f"(end: {end_time_dt}, offset: {config.BID_OFFSET_SECONDS}s)"
        )

    def unschedule_watch(self, watch_id: str):
        """Remove scheduled jobs for a watch

        Args:
            watch_id: Watch ID
        """
        snipe_job_id = f"snipe_{watch_id}"
        check_job_id = f"check_{watch_id}"

        try:
            self.scheduler.remove_job(snipe_job_id)
            logger.info(f"Removed snipe job for watch {watch_id}")
        except Exception:
            pass  # Job may not exist

        try:
            self.scheduler.remove_job(check_job_id)
            logger.info(f"Removed check job for watch {watch_id}")
        except Exception:
            pass  # Job may not exist

    async def _execute_snipe_wrapper(self, watch_id: str):
        """Wrapper for execute_snipe that handles errors"""
        try:
            logger.info(f"Executing snipe for watch {watch_id}")
            result = await self.sniper.execute_snipe(watch_id)

            # If snipe failed, schedule retry
            if not result.get("success"):
                watch = self.db.get_watch(watch_id)
                if watch and watch["status"] == "active":
                    # Schedule retry at end_time - BID_RETRY_OFFSET_SECONDS
                    end_time = datetime.fromisoformat(watch["auction_end_time"])
                    retry_time = end_time - timedelta(
                        seconds=config.BID_RETRY_OFFSET_SECONDS
                    )
                    now = self.ntp.get_adjusted_time()

                    # Only retry if retry_time is in the future
                    if retry_time > now:
                        retry_job_id = f"snipe_retry_{watch_id}"
                        self.scheduler.add_job(
                            func=execute_snipe_job,
                            trigger=DateTrigger(
                                run_date=retry_time, timezone=timezone.utc
                            ),
                            id=retry_job_id,
                            args=[watch_id],
                            replace_existing=True,
                        )
                        logger.info(
                            f"Scheduled retry for watch {watch_id} at {retry_time}"
                        )

        except Exception as e:
            logger.error(f"Error executing snipe for watch {watch_id}: {e}")
            self.db.log_event(watch_id, "error", {"error": str(e)})

    async def _check_result_wrapper(self, watch_id: str):
        """Wrapper for check_result that handles errors"""
        try:
            logger.info(f"Checking result for watch {watch_id}")
            result = await self.sniper.check_result(watch_id)
            logger.info(f"Result check for watch {watch_id}: {result}")
        except Exception as e:
            logger.error(f"Error checking result for watch {watch_id}: {e}")

    def get_scheduled_jobs(self) -> list[dict]:
        """Get list of scheduled jobs

        Returns:
            List of job info dicts
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run_time = getattr(job, "next_run_time", None)
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        next_run_time.isoformat() if next_run_time else None
                    ),
                }
            )
        return jobs
