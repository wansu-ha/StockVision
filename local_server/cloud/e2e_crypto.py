"""E2E 암호화 모듈 — AES-256-GCM.

로컬 서버에서 금융 데이터를 디바이스별로 암호화.
키는 ~/.stockvision/device_keys/ 디렉토리에 저장.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

KEY_DIR = Path.home() / ".stockvision" / "device_keys"


class E2ECrypto:
    """AES-256-GCM 기반 E2E 암호화."""

    def __init__(self, key_store_path: Path | None = None) -> None:
        self._key_dir = key_store_path or KEY_DIR
        self._key_dir.mkdir(parents=True, exist_ok=True)
        # device_id → bytes (32바이트 AES-256 키)
        self._keys: dict[str, bytes] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """디스크에서 키 로드."""
        for f in self._key_dir.glob("*.key"):
            device_id = f.stem
            key_b64 = f.read_text(encoding="utf-8").strip()
            try:
                self._keys[device_id] = base64.b64decode(key_b64)
            except Exception as e:
                logger.error("키 로드 실패: device=%s, error=%s", device_id, e)

    def encrypt(self, plaintext: dict, device_id: str) -> dict | None:
        """단일 디바이스용 암호화. 키가 없으면 None."""
        key = self._keys.get(device_id)
        if key is None:
            return None

        data = json.dumps(plaintext, ensure_ascii=False).encode("utf-8")
        iv = os.urandom(12)  # 96-bit nonce
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(iv, data, None)

        # GCM: ciphertext + tag (마지막 16바이트)
        ciphertext = ct[:-16]
        tag = ct[-16:]

        return {
            "iv": base64.b64encode(iv).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "tag": base64.b64encode(tag).decode(),
        }

    def encrypt_for_all(self, plaintext: dict) -> dict:
        """등록된 모든 디바이스용 암호화. encrypted_for 형식 반환."""
        result: dict[str, dict] = {}
        for device_id in self._keys:
            encrypted = self.encrypt(plaintext, device_id)
            if encrypted:
                result[device_id] = encrypted
        return result

    def decrypt(self, encrypted: dict, device_id: str) -> dict | None:
        """복호화 (테스트 및 로컬 검증용)."""
        key = self._keys.get(device_id)
        if key is None:
            return None

        iv = base64.b64decode(encrypted["iv"])
        ciphertext = base64.b64decode(encrypted["ciphertext"])
        tag = base64.b64decode(encrypted["tag"])

        aesgcm = AESGCM(key)
        ct_with_tag = ciphertext + tag
        data = aesgcm.decrypt(iv, ct_with_tag, None)
        return json.loads(data.decode("utf-8"))

    def generate_key(self) -> tuple[str, str]:
        """새 디바이스 키 생성. (device_id, key_base64) 반환."""
        from uuid import uuid4
        device_id = str(uuid4())[:8]
        key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.b64encode(key).decode()

        # 디스크에 저장
        self.register_key(device_id, key)

        return device_id, key_b64

    def register_key(self, device_id: str, key: bytes) -> None:
        """디바이스 키 등록."""
        self._keys[device_id] = key
        key_path = self._key_dir / f"{device_id}.key"
        key_path.write_text(base64.b64encode(key).decode(), encoding="utf-8")
        logger.info("디바이스 키 등록: device=%s", device_id)

    def revoke_key(self, device_id: str) -> None:
        """디바이스 키 폐기."""
        self._keys.pop(device_id, None)
        key_path = self._key_dir / f"{device_id}.key"
        if key_path.exists():
            key_path.unlink()
        logger.info("디바이스 키 폐기: device=%s", device_id)

    def has_devices(self) -> bool:
        return bool(self._keys)

    def device_ids(self) -> list[str]:
        return list(self._keys.keys())
