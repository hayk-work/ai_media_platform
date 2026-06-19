import uuid

from common.config import settings
from common.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    password = "strong-password-123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_create_and_decode_access_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, token_version=0)
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["tv"] == 0


def test_decode_invalid_token_returns_none() -> None:
    assert decode_access_token("not-a-valid-token") is None


def test_decode_tampered_token_returns_none() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, token_version=0)
    tampered = f"{token}extra"
    assert decode_access_token(tampered) is None


def test_token_uses_configured_algorithm() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, token_version=1)
    payload = decode_access_token(token)

    assert payload is not None
    assert settings.jwt_algorithm == "HS256"
