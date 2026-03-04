"""
하트비트 워커

5분 주기로 클라우드에 익명 UUID + 버전 정보 전송.
서버 모니터링용 (개인정보 없음).
"""
import asyncio
import logging
import os
import uuid

import httpx

logger = logging.getLogger(__name__)

_CLOUD_URL = os.environ.get("CLOUD_URL", "https://stockvision.app")
_INTERVAL  = 300  # 5분
_VERSION   = "1.0.0"
_BRIDGE_ID = str(uuid.uuid4())  # 프로세스 생존 동안 고정 (재시작 시 변경)


class HeartbeatWorker:
    async def run(self) -> None:
        while True:
            await asyncio.sleep(_INTERVAL)
            await self._send()

    async def _send(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{_CLOUD_URL}/api/heartbeat",
                    json={"bridge_id": _BRIDGE_ID, "version": _VERSION},
                    timeout=5,
                )
        except Exception as e:
            logger.debug(f"하트비트 전송 실패 (무시): {e}")
