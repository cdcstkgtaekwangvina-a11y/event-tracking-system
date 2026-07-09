import os
import logging
from uuid import UUID
from arq.worker import func
from database.models.app_db import async_session_factory, engine
from database.models.employees import Employees
from database.models.queue_jobs import JobStatus
from src.modules.queue_job.queue_job_services import QueueJobServices
from src.modules.employees.employee_services import EmployeeServices
from src.shared.constants.queue_keys import QueueKeys
from src.shared.queues.base_queue import redis_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arq.worker")



async def startup(ctx):
    logger.info("Starting up arq worker...")


async def shutdown(ctx):
    logger.info("Shutting down arq worker...")
    await engine.dispose()
    logger.info("Database connections disposed.")


async def bulk_upsert_employees_task(ctx, employees_data: list[dict]) -> dict:
    """Task to bulk upsert employees in background, tracking progress in database."""
    job_id_str = ctx.get("job_id")
    logger.info(f"Received bulk upsert task for {len(employees_data)} employees. Job ID: {job_id_str}")
    
    job_uuid = UUID(job_id_str) if job_id_str else None
    job_services = QueueJobServices()
    
    # 1. Update status to RUNNING
    if job_uuid:
        await job_services.update_job(
            job_id=job_uuid,
            status=JobStatus.RUNNING,
            progress=0,
            log_message="Job started processing in background worker."
        )

    try:
        total_records = len(employees_data)
        if total_records == 0:
            if job_uuid:
                await job_services.update_job(
                    job_id=job_uuid,
                    status=JobStatus.SUCCESS,
                    progress=100,
                    log_message="Completed bulk upsert for 0 employees.",
                    finished=True
                )
            return {"status": "success", "added_count": 0, "updated_count": 0}

        # Chunk size for progress tracking
        chunk_size = max(1, total_records // 10)  # e.g., updates progress in ~10 steps
        if chunk_size > 100:
            chunk_size = 100  # Cap chunk size to 100 for smoother updates

        added_total = 0
        updated_total = 0
        
        # Loop through employees in chunks
        for i in range(0, total_records, chunk_size):
            chunk_data = employees_data[i : i + chunk_size]
            
            # Convert dictionaries to SQLModel instances
            employees_chunk = [Employees.model_validate(emp_dict) for emp_dict in chunk_data]
            
            # Process chunk database upsert
            async with async_session_factory() as session:
                service = EmployeeServices(session=session, session_factory=async_session_factory)
                result = await service.bulk_upsert_employees_db(employees_chunk)
                
            if result:
                added_total += len(result.added_employees)
                updated_total += len(result.updated_employees)
                
            # Update progress dynamically
            processed_count = min(i + chunk_size, total_records)
            progress_pct = int((processed_count / total_records) * 100)
            
            if job_uuid:
                await job_services.update_job(
                    job_id=job_uuid,
                    progress=progress_pct,
                    log_message=f"Processed chunk {processed_count}/{total_records} ({progress_pct}%)."
                )

        logger.info(f"Successfully processed bulk upsert: added {added_total}, updated {updated_total}")
        
        # 2. Update status to SUCCESS
        if job_uuid:
            await job_services.update_job(
                job_id=job_uuid,
                status=JobStatus.SUCCESS,
                progress=100,
                log_message=f"Successfully processed bulk upsert: added {added_total}, updated {updated_total}.",
                finished=True
            )
            
        return {
            "status": "success",
            "added_count": added_total,
            "updated_count": updated_total
        }
    except Exception as e:
        logger.exception(f"Error during bulk upsert task: {e}")
        
        # 3. Update status to FAILED
        if job_uuid:
            await job_services.update_job(
                job_id=job_uuid,
                status=JobStatus.FAILED,
                log_error=str(e),
                finished=True
            )
            
        return {
            "status": "failed",
            "error": str(e)
        }


class WorkerSettings:
    """arq worker configuration class."""
    functions = [
        func(bulk_upsert_employees_task, name=QueueKeys.BULK_UPSERT_EMPLOYEES.value)
    ]
    redis_settings = redis_settings
    on_startup = startup
    on_shutdown = shutdown
