from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    """비밀번호 → Argon2id 해시"""
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """비밀번호 검증. 일치하면 True"""
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
