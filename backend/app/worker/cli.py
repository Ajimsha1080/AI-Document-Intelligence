import asyncio
import logging
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.worker.tasks import process_document_pipeline
from app.worker.queue import get_redis_client

logger = logging.getLogger("worker_cli")

def run_worker_job(document_id: str, tenant_id: str):
    """Entrypoint called by RQ Worker."""
    return asyncio.run(process_document_pipeline(document_id, tenant_id))

def main():
    """Runs continuous RQ worker listening on Redis queue."""
    conn = get_redis_client()
    if not conn:
        logger.error("Cannot start RQ worker: Redis connection unavailable.")
        sys.exit(1)

    from rq import Worker, Queue
    queue = Queue("document_pipeline", connection=conn)
    worker = Worker([queue], connection=conn)
    logger.info("Starting Sovereign Document Intelligence RQ Worker on 'document_pipeline' queue...")
    worker.work()

if __name__ == "__main__":
    main()
