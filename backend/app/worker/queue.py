import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("worker_queue")

_redis_conn = None
_rq_queue = None

def get_redis_client():
    global _redis_conn
    if _redis_conn is None:
        try:
            import redis
            _redis_conn = redis.from_url(settings.REDIS_URL, decode_responses=False)
            _redis_conn.ping()
        except Exception as e:
            _redis_conn = None
            logger.info(f"Redis queue unavailable ({e}). Running jobs in direct/sync mode.")
    return _redis_conn

def get_job_queue():
    global _rq_queue
    conn = get_redis_client()
    if conn and _rq_queue is None:
        try:
            from rq import Queue
            _rq_queue = Queue("document_pipeline", connection=conn, default_timeout=300)
        except Exception as e:
            logger.warning(f"Failed to initialize RQ Queue: {e}")
            _rq_queue = None
    return _rq_queue

def enqueue_document_job(document_id: str, tenant_id: str) -> Optional[str]:
    """
    Enqueues document processing job with timeout and retry backoff.
    Returns job_id or None.
    """
    queue = get_job_queue()
    if queue:
        try:
            from rq import Retry
            job = queue.enqueue(
                "app.worker.cli.run_worker_job",
                args=(document_id, tenant_id),
                job_timeout=300,
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            logger.info(f"Document {document_id} enqueued to RQ job {job.id}")
            return job.id
        except Exception as e:
            logger.error(f"Failed to enqueue to RQ ({e}).")
    return None
