from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_round_trip():
    token = create_access_token("42")
    assert decode_access_token(token) == "42"
