import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("worker_queue")

_redis_conn = None
_worker_redis_conn = None
_rq_queue = None
_redis_last_check = 0.0
_redis_check_interval = 10.0  # seconds between reconnection attempts

def get_redis_client():
    global _redis_conn, _redis_last_check
    import time
    now = time.time()
    if _redis_conn is None and (now - _redis_last_check) > _redis_check_interval:
        _redis_last_check = now
        try:
            import redis
            conn = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=0.2,
                socket_timeout=0.5
            )
            conn.ping()
            _redis_conn = conn
        except Exception as e:
            _redis_conn = None
            logger.info(f"Redis queue unavailable ({e}). Running jobs in direct/sync mode.")
    return _redis_conn

def get_worker_redis_client():
    """
    Dedicated worker Redis connection with NO socket timeout.
    RQ workers block indefinitely on BLPOP; a short socket_timeout causes crashes.
    """
    global _worker_redis_conn
    if _worker_redis_conn is None:
        try:
            import redis
            conn = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=5.0,
                socket_timeout=None
            )
            conn.ping()
            _worker_redis_conn = conn
        except Exception as e:
            logger.error(f"Worker Redis connection failed ({e})")
            _worker_redis_conn = None
    return _worker_redis_conn

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
    
    # Standalone fallback when Redis / RQ is unavailable
    try:
        import threading
        from app.worker.cli import run_worker_job
        worker_thread = threading.Thread(target=run_worker_job, args=(document_id, tenant_id), daemon=True)
        worker_thread.start()
        logger.info(f"Document {document_id} running via local background worker thread.")
        return f"thread-{document_id}"
    except Exception as e:
        logger.error(f"Failed to spawn local worker thread ({e}).")
        return None
