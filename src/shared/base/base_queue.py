import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def queue_job(key: str):
    """Decorator đánh dấu hàm bên trong class là một queue job"""

    def decorator(func):
        func._queue_key = key
        return func

    return decorator


class QueueServices:
    def __init__(self):
        self.job_queue = asyncio.Queue()
        self.scheduler = AsyncIOScheduler()
        self.worker_task = None
        self._registry = {}

    def register_class(self, cls):
        """Class Decorator để tự động khởi tạo class và đăng ký tất cả @queue_job"""
        instance = cls()

        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if callable(attr):
                underlying_func = getattr(attr, "__func__", attr)

                if hasattr(underlying_func, "_queue_key"):
                    key = getattr(underlying_func, "_queue_key")
                    self._registry[key] = attr
                    logger.info(
                        f"📌 Đã đăng ký queue job: {key} -> {cls.__name__}.{attr_name}"
                    )
        return cls

    async def _queue_worker(self):
        logger.info("🤖 Background Job Queue Worker đã kích hoạt...")
        while True:
            try:
                job_type, payload = await self.job_queue.get()
                func = self._registry.get(job_type)
                if func:
                    await func(payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Lỗi xử lý task ngầm: {e}")
            finally:
                self.job_queue.task_done()

    async def fill_job_from_db(self):
        from sqlmodel import select

        from database.models.app_db import async_session_factory
        from database.models.queue_jobs import JobStatus, QueueJob

        async with async_session_factory() as session:
            stmt = select(QueueJob).where(QueueJob.status == JobStatus.RUNNING.value)
            result = await session.exec(stmt)
            pending_jobs = result.all()

            if not pending_jobs:
                return

            for job in pending_jobs:
                if job.next_payload:
                    await self.enqueue_by_type(job.type, job.next_payload)

    def add_cron_job(self, func, cron_expression: str, **kwargs):
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(func, trigger, **kwargs)

    async def enqueue_by_type(self, job_type: str, payload: Any):
        func = self._registry.get(job_type)
        if not func:
            raise ValueError(f"Loại job '{job_type}' không tồn tại trong hệ thống!")
        await self.job_queue.put((func, payload))

    async def start(self):
        self.scheduler.start()
        self.worker_task = asyncio.create_task(self._queue_worker())
        logger.info("🚀 Toàn bộ phân hệ Background Services đã sẵn sàng!")

    async def stop(self):
        self.scheduler.shutdown()

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Đã dừng toàn bộ Background Services.")


queue_service = QueueServices()
