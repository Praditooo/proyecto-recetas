import os

# Variables mínimas ANTES de importar la app (no se usamos credenciales reales en pruebas).
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "clave-solo-para-pruebas")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import login_limiter  # noqa: E402

USER = {"email": "ana@example.com", "full_name": "Ana", "password": "secreto123"}


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    login_limiter.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def auth_headers(client):
    client.post("/api/auth/register", json=USER)
    res = client.post("/api/auth/login", data={"username": USER["email"], "password": USER["password"]})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
