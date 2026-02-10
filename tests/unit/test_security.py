from app.core.security import get_password_hash, verify_password


def test_password_hash_and_verify():
    plain = "StrongPass123"
    hashed = get_password_hash(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPass123", hashed) is False
