"""클라우드 하트비트 전송 모듈.

설정된 간격으로 클라우드 서버에 로컬 서버 상태를 전송한다.
클라우드 서버는 하트비트를 통해 로컬 서버의 온라인/오프라인 상태를 파악한다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from local_server.cloud.client import CloudClient, CloudClientError
from local_server.config import get_config
from local_server.routers.status import is_strategy_running

logger = logging.getLogger(__name__)


def _build_heartbeat_payload() -> dict[str, Any]:
    """현재 로컬 서버 상태를 담은 하트비트 페이로드를 생성한다."""
    return {
        "status": "online",
        "strategy_engine": "running" if is_strategy_running() else "stopped",
    }


async def start_heartbeat() -> None:
    """하트비트 전송 루프를 실행한다.

    asyncio.CancelledError 발생 시 종료된다.
    전송 실패는 경고 로그로 기록하고 계속 실행한다.
    """
    cfg = get_config()
    cloud_url = cfg.get("cloud.url", "")
    interval = cfg.get("cloud.heartbeat_interval", 30)

    if not cloud_url:
        logger.warning("cloud.url이 설정되지 않아 하트비트를 시작할 수 없습니다.")
        return

    client = CloudClient(base_url=cloud_url)
    logger.info("하트비트 시작: 간격=%ds, 대상=%s", interval, cloud_url)

    while True:
        try:
            payload = _build_heartbeat_payload()
            await client.send_heartbeat(payload)
            logger.debug("하트비트 전송 완료")
        except CloudClientError as e:
            logger.warning("하트비트 전송 실패 (재시도 예정): %s", e)
        except asyncio.CancelledError:
            logger.info("하트비트 루프 종료")
            break
        except Exception as e:
            logger.error("하트비트 예상치 못한 오류: %s", e)

        await asyncio.sleep(interval)
