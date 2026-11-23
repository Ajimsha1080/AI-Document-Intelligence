import asyncio
import logging
import sys
import os
import threading
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.worker.tasks import process_document_pipeline
from app.worker.queue import get_worker_redis_client

logger = logging.getLogger("worker_cli")

def run_worker_job(document_id: str, tenant_id: str):
    """Entrypoint called by RQ Worker."""
    return asyncio.run(process_document_pipeline(document_id, tenant_id))

def start_scheduler_thread():
    """Starts background daemon thread running stuck-job sweeper (1 min) and retention sweep (daily)."""
    async def periodic_tasks():
        last_retention_run = 0.0
        from app.core.database import create_worker_engine, create_worker_sessionmaker
        from app.worker.sweeper import sweep_stuck_jobs
        from app.services.retention_service import run_retention_policy_sweep

        worker_engine = create_worker_engine()
        worker_session_maker = create_worker_sessionmaker(worker_engine)
        try:
            while True:
                try:
                    # 1. Stuck-job sweeper every 1 minute
                    async with worker_session_maker() as session:
                        await sweep_stuck_jobs(session)

                    # 2. Retention policy sweep daily (every 86400s)
                    now = time.time()
                    if (now - last_retention_run) >= 86400:
                        last_retention_run = now
                        async with worker_session_maker() as session:
                            await run_retention_policy_sweep(session)
                except Exception as e:
                    logger.error(f"Error in worker scheduler loop: {e}")

                await asyncio.sleep(60)
        finally:
            await worker_engine.dispose()

    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(periodic_tasks())

    t = threading.Thread(target=run_loop, daemon=True, name="WorkerScheduler")
    t.start()
    logger.info("Worker scheduler thread started (stuck-job sweeper every 1m, retention daily).")

def main():
    """Runs continuous RQ worker listening on Redis queue."""
    conn = get_worker_redis_client()
    if not conn:
        logger.error("Cannot start RQ worker: Redis connection unavailable.")
        sys.exit(1)

    start_scheduler_thread()

    from rq import Worker, Queue
    queue = Queue("document_pipeline", connection=conn)
    worker = Worker([queue], connection=conn)
    logger.info("Starting Sovereign Document Intelligence RQ Worker on 'document_pipeline' queue...")
    worker.work()

if __name__ == "__main__":
    main()
