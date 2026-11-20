"""Limitador simple de intentos fallidos de login (en memoria)."""
import time


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300, clock=time.monotonic):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        now = self._clock()
        attempts = [t for t in self._failures.get(key, []) if now - t <= self.window_seconds]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def is_blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        attempts = self._recent(key)
        attempts.append(self._clock())
        self._failures[key] = attempts

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def retry_after(self, key: str) -> int:
        attempts = self._recent(key)
        if not attempts:
            return 0
        return max(1, int(self.window_seconds - (self._clock() - attempts[0])) + 1)

    def clear(self) -> None:
        self._failures.clear()


login_limiter = LoginRateLimiter()