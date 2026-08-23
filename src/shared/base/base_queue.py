import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.shared.base.base_logger import get_logger

logger = get_logger(__name__)


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
        self._running_tasks: dict[str, asyncio.Task] = {}

    def register_class(self, cls):
        """Class Decorator để tự động khởi tạo class và đăng ký tất cả @queue_job"""
        instance = cls()

        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if callable(attr):
                underlying_func = getattr(attr, "__func__", attr)

                if hasattr(underlying_func, "_queue_key"):
                    key = underlying_func._queue_key
                    self._registry[key] = attr
                    logger.info(
                        f"📌 Đã đăng ký queue job: {key} -> {cls.__name__}.{attr_name}"
                    )
        return cls

    async def _queue_worker(self):
        logger.info("🤖 Background Job Queue Worker đã kích hoạt...")
        while True:
            try:
                job_id, job_type = await self.job_queue.get()
            except asyncio.CancelledError:
                break

            try:
                func = self._registry.get(job_type)

                if func:
                    task = asyncio.create_task(func(job_id))
                    self._running_tasks[job_id] = task

                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.warning(
                            f"⚠️ Job {job_id} ({job_type}) đã bị hủy mid-way!"
                        )
                    finally:
                        self._running_tasks.pop(job_id, None)

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
                    await self.enqueue_by_type(job.type, str(job.id))

    def add_cron_job(self, func, cron_expression: str, **kwargs):
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(func, trigger, **kwargs)

    async def enqueue_by_type(self, job_type: str, job_id: str):
        if job_type not in self._registry:
            raise ValueError(f"Loại job '{job_type}' không tồn tại trong hệ thống!")

        # Đẩy kèm job_id để quản lý
        await self.job_queue.put((job_id, job_type))

    def cancel_job(self, job_id: str) -> bool:
        """Hủy 1 job đang chạy theo job_id"""
        task = self._running_tasks.get(job_id)

        if task and not task.done():
            task.cancel()
            logger.info(f"🛑 Đã gửi lệnh hủy cho job: {job_id}")
            return True

        logger.warning(f"⚠️ Không thể hủy job {job_id}: Job không tồn tại hoặc đã xong.")
        return False

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
