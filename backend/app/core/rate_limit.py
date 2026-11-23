import time
from typing import Dict, Tuple
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from app.core.config import settings

import time
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger("rate_limit")

def _get_redis():
    try:
        from app.worker.queue import get_redis_client
        return get_redis_client()
    except Exception:
        return None

class LoginRateLimiter:
    """
    Sliding window rate limiter and brute-force lockout guard for authentication.
    Complies with UAE banking KYC security requirements.
    Tracks failed attempts across (IP + email) and per email alone across IPs.
    Supports Redis persistence across processes with graceful in-memory fallback.
    """
    def __init__(self):
        # Maps key -> list of failure timestamps
        self._failures: Dict[str, list] = {}
        # Maps key -> lockout expiry timestamp
        self._lockouts: Dict[str, float] = {}

    def _keys(self, ip: str, email: str) -> Tuple[str, str]:
        clean_ip = ip.strip()
        clean_email = email.strip().lower()
        return f"ip_email:{clean_ip}:{clean_email}", f"email:{clean_email}"

    def is_locked_out(self, ip: str, email: str) -> Tuple[bool, int]:
        """Returns (is_locked, remaining_seconds). Checks both (ip, email) and email alone."""
        ip_email_key, email_key = self._keys(ip, email)
        now = time.time()

        r = _get_redis()
        if r:
            try:
                for k in (email_key, ip_email_key):
                    ttl = r.ttl(f"ratelimit:lockout:{k}")
                    if ttl and ttl > 0:
                        return True, ttl
            except Exception as e:
                logger.debug(f"Redis lockout check fallback to memory: {e}")

        # In-memory check
        for k in (email_key, ip_email_key):
            lockout_time = self._lockouts.get(k)
            if lockout_time:
                if now < lockout_time:
                    remaining = int(lockout_time - now)
                    return True, max(1, remaining)
                else:
                    self._lockouts.pop(k, None)
                    self._failures.pop(k, None)

        return False, 0

    def check_lockout(self, ip: str, email: str) -> None:
        """Raises HTTP 429 Too Many Requests if account or IP is temporarily locked out."""
        locked, remaining_seconds = self.is_locked_out(ip, email)
        if locked:
            remaining_mins = max(1, (remaining_seconds + 59) // 60)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Security lockout: Too many failed login attempts. "
                    f"Temporary lockout active. Please try again in {remaining_mins} minute(s)."
                ),
                headers={"Retry-After": str(remaining_seconds)}
            )

    def record_failure(self, ip: str, email: str) -> bool:
        """
        Records a failed login attempt for both (ip, email) and email alone.
        If failed attempts reach LOGIN_MAX_FAILED_ATTEMPTS on either, engages lockout.
        """
        ip_email_key, email_key = self._keys(ip, email)
        now = time.time()
        window_seconds = settings.LOGIN_LOCKOUT_MINUTES * 60
        max_attempts = settings.LOGIN_MAX_FAILED_ATTEMPTS
        is_now_locked = False

        r = _get_redis()
        if r:
            try:
                for k in (email_key, ip_email_key):
                    fail_key = f"ratelimit:failures:{k}"
                    pipe = r.pipeline()
                    pipe.rpush(fail_key, str(now))
                    pipe.expire(fail_key, window_seconds)
                    res = pipe.execute()
                    count = res[0]
                    if count >= max_attempts:
                        r.set(f"ratelimit:lockout:{k}", "1", ex=window_seconds)
                        is_now_locked = True
                if is_now_locked:
                    return True
            except Exception as e:
                logger.debug(f"Redis record_failure fallback to memory: {e}")

        for k in (email_key, ip_email_key):
            timestamps = [t for t in self._failures.get(k, []) if now - t < window_seconds]
            timestamps.append(now)
            self._failures[k] = timestamps
            if len(timestamps) >= max_attempts:
                self._lockouts[k] = now + window_seconds
                is_now_locked = True

        return is_now_locked

    def record_success(self, ip: str, email: str) -> None:
        """Clears failure counters upon successful authentication."""
        ip_email_key, email_key = self._keys(ip, email)
        r = _get_redis()
        if r:
            try:
                for k in (email_key, ip_email_key):
                    r.delete(f"ratelimit:failures:{k}", f"ratelimit:lockout:{k}")
            except Exception:
                pass

        for k in (email_key, ip_email_key):
            self._failures.pop(k, None)
            self._lockouts.pop(k, None)

    def reset(self) -> None:
        """Utility for test suite and system resets."""
        self._failures.clear()
        self._lockouts.clear()

login_rate_limiter = LoginRateLimiter()
