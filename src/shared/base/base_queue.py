from database.models.app_db import async_session_factory
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends
from typing import Annotated, Any
from src.subscription_services.subscription_queue import JOB_MAP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueueServices:
    def __init__(self):
        self.job_queue = asyncio.Queue()

        self.scheduler = AsyncIOScheduler()

        self.worker_task = None

    async def _queue_worker(self):
        """Worker chạy ngầm vĩnh viễn để lôi các job trong Queue ra xử lý"""
        logger.info("🤖 Background Job Queue Worker đã kích hoạt...")
        while True:
            func, payload = await self.job_queue.get()
            try:
                await func(payload)
            except Exception as e:
                logger.error(f"❌ Lỗi xử lý task ngầm: {e}")
            finally:
                self.job_queue.task_done()

    async def fill_job_from_db(self):
        from sqlmodel import select
        from database.models.queue_jobs import QueueJob, JobStatus

        async with async_session_factory() as session:
            stmt = select(QueueJob).where(QueueJob.status == JobStatus.RUNNING.value)
            result = await session.exec(stmt)
            pending_job = result.all()

            if not pending_job:
                return

            for job in pending_job:
                payload = job.next_payload

                if payload:
                    await self.enqueue_by_type(job.type, payload)

    def add_cron_job(self, func, cron_expression: str, **kwargs):
        """Đăng ký một Cron Job chạy định kỳ bằng cú pháp chuẩn của Linux Cron"""
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(func, trigger, **kwargs)

    async def enqueue_by_type(self, job_type: str, payload: Any):
        func = JOB_MAP.get(job_type)

        if not func:
            raise ValueError(f"Loại job '{job_type}' không tồn tại trong hệ thống!")

        await self.job_queue.put((func, payload))

    async def start(self):
        """Kích hoạt toàn bộ hệ thống chạy ngaming (Tương đương Host.StartAsync)"""
        self.scheduler.start()
        self.worker_task = asyncio.create_task(self._queue_worker())
        logger.info("🚀 Toàn bộ phân hệ Background Services đã sẵn sàng!")

    async def stop(self):
        """Dừng an toàn (Tương đương Host.StopAsync)"""
        self.scheduler.shutdown()
        if self.worker_task:
            self.worker_task.cancel()
        logger.info("🛑 Đã dừng toàn bộ Background Services.")


QueueServiceDep = Annotated[QueueServices, Depends()]
