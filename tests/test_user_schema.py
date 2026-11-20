import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


def _data(password: str) -> dict:
    return {"email": "ana@example.com", "full_name": "Ana", "password": password}


def test_accepts_password_with_letters_and_digits():
    assert UserCreate(**_data("secreto123")).password == "secreto123"


@pytest.mark.parametrize("password", ["sololetras", "12345678"])
def test_rejects_password_without_letters_or_digits(password):
    with pytest.raises(ValidationError):
        UserCreate(**_data(password))


def test_register_endpoint_rejects_weak_password(client):
    res = client.post("/api/auth/register", json=_data("sololetras"))
    assert res.status_code == 422