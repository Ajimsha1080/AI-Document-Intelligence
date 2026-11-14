import time
from typing import Dict, Tuple
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from app.core.config import settings

class LoginRateLimiter:
    """
    Sliding window rate limiter and brute-force lockout guard for authentication.
    Complies with UAE banking KYC security requirements.
    Tracks failed attempts across IP address and user account email.
    """
    def __init__(self):
        # Maps (ip, email) -> list of failure timestamps
        self._failures: Dict[Tuple[str, str], list] = {}
        # Maps (ip, email) -> lockout expiry timestamp
        self._lockouts: Dict[Tuple[str, str], float] = {}

    def _get_key(self, ip: str, email: str) -> Tuple[str, str]:
        return (ip.strip(), email.strip().lower())

    def is_locked_out(self, ip: str, email: str) -> Tuple[bool, int]:
        """Returns (is_locked, remaining_seconds)."""
        key = self._get_key(ip, email)
        now = time.time()
        
        lockout_time = self._lockouts.get(key)
        if lockout_time:
            if now < lockout_time:
                remaining = int(lockout_time - now)
                return True, max(1, remaining)
            else:
                # Lockout expired, clean up
                del self._lockouts[key]
                self._failures.pop(key, None)
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
        Records a failed login attempt.
        If failed attempts reach LOGIN_MAX_FAILED_ATTEMPTS, engages lockout.
        Returns True if newly locked out.
        """
        key = self._get_key(ip, email)
        now = time.time()
        window_seconds = settings.LOGIN_LOCKOUT_MINUTES * 60
        
        # Clean older entries outside window
        timestamps = [t for t in self._failures.get(key, []) if now - t < window_seconds]
        timestamps.append(now)
        self._failures[key] = timestamps

        if len(timestamps) >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            self._lockouts[key] = now + window_seconds
            return True
        return False

    def record_success(self, ip: str, email: str) -> None:
        """Clears failure counters upon successful authentication."""
        key = self._get_key(ip, email)
        self._failures.pop(key, None)
        self._lockouts.pop(key, None)

    def reset(self) -> None:
        """Utility for test suite isolation."""
        self._failures.clear()
        self._lockouts.clear()

login_rate_limiter = LoginRateLimiter()
