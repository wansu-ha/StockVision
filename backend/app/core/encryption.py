import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    key_hex = os.environ.get("CONFIG_ENCRYPTION_KEY", "")
    if not key_hex:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다.")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY는 64자리 hex (32바이트)여야 합니다.")
    return key


def encrypt_blob(data: bytes) -> bytes:
    """평문 바이트 → nonce(12B) + ciphertext (AES-256-GCM)"""
    nonce = os.urandom(12)
    return nonce + AESGCM(_get_key()).encrypt(nonce, data, None)


def decrypt_blob(blob: bytes) -> bytes:
    """nonce(12B) + ciphertext → 평문 바이트"""
    if len(blob) < 28:  # 12(nonce) + 16(GCM tag) 최소
        raise ValueError("잘못된 blob 형식")
    return AESGCM(_get_key()).decrypt(blob[:12], blob[12:], None)
