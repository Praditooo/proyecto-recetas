from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import get_settings
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("secreto123")
    assert hashed != "secreto123"
    assert verify_password("secreto123", hashed)


def test_wrong_password_does_not_verify():
    assert not verify_password("otra-clave", hash_password("secreto123"))


def test_hash_is_salted():
    assert hash_password("secreto123") != hash_password("secreto123")


def test_access_token_roundtrip():
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_is_rejected():
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(expired) is None


def test_token_signed_with_other_key_is_rejected():
    forged = jwt.encode({"sub": "1"}, "otra-clave-distinta", algorithm="HS256")
    assert decode_access_token(forged) is None


def test_garbage_token_is_rejected():
    assert decode_access_token("esto-no-es-un-token") is None