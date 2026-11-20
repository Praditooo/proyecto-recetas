from app.rate_limit import LoginRateLimiter
from tests.conftest import USER


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_blocks_after_max_failures():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, clock=FakeClock())
    for _ in range(3):
        limiter.register_failure("k")
    assert limiter.is_blocked("k")


def test_failures_expire_after_window():
    clock = FakeClock()
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, clock=clock)
    for _ in range(3):
        limiter.register_failure("k")
    clock.now = 61
    assert not limiter.is_blocked("k")


def test_reset_and_independent_keys():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60, clock=FakeClock())
    limiter.register_failure("a")
    limiter.register_failure("a")
    assert limiter.is_blocked("a")
    assert not limiter.is_blocked("b")
    limiter.reset("a")
    assert not limiter.is_blocked("a")


def test_login_is_blocked_after_repeated_failures(client):
    client.post("/api/auth/register", json=USER)
    bad = {"username": USER["email"], "password": "incorrecta1"}
    for _ in range(5):
        assert client.post("/api/auth/login", data=bad).status_code == 401

    res = client.post("/api/auth/login", data=bad)
    assert res.status_code == 429
    assert "retry-after" in res.headers

    good = {"username": USER["email"], "password": USER["password"]}
    assert client.post("/api/auth/login", data=good).status_code == 429


def test_successful_login_resets_counter(client):
    client.post("/api/auth/register", json=USER)
    bad = {"username": USER["email"], "password": "incorrecta1"}
    good = {"username": USER["email"], "password": USER["password"]}
    for _ in range(4):
        client.post("/api/auth/login", data=bad)
    assert client.post("/api/auth/login", data=good).status_code == 200
    for _ in range(4):
        assert client.post("/api/auth/login", data=bad).status_code == 401