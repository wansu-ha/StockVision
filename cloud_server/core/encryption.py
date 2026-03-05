"""
AES-256-GCM 암호화 (서비스 키 등 설정 blob 용)

기존 backend/app/core/encryption.py와 동일한 로직.
CONFIG_ENCRYPTION_KEY 환경변수 (64자리 hex = 32바이트)
"""
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from cloud_server.core.config import settings


def _get_key() -> bytes:
    key_hex = settings.CONFIG_ENCRYPTION_KEY
    if not key_hex:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다.")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY는 64자리 hex (32바이트)여야 합니다.")
    return key


def encrypt_value(data: str) -> str:
    """평문 문자열 → nonce(12B) + ciphertext (hex 문자열)"""
    nonce = os.urandom(12)
    encrypted = nonce + AESGCM(_get_key()).encrypt(nonce, data.encode(), None)
    return encrypted.hex()


def decrypt_value(hex_blob: str) -> str:
    """hex 문자열 → 복호화된 평문 문자열"""
    blob = bytes.fromhex(hex_blob)
    if len(blob) < 28:  # 12(nonce) + 16(GCM tag) 최소
        raise ValueError("잘못된 blob 형식")
    plain = AESGCM(_get_key()).decrypt(blob[:12], blob[12:], None)
    return plain.decode()
