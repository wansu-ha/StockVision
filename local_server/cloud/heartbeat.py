"""클라우드 하트비트 전송 모듈.

설정된 간격으로 클라우드 서버에 로컬 서버 상태를 전송한다.
하트비트 응답에서 버전 변경을 감지하여 규칙/컨텍스트를 자동 fetch한다.
연속 실패 시 트레이 아이콘 색상을 변경한다 (5분→🟡, 30분→🔴).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from local_server.cloud.client import CloudClient, CloudClientError
from local_server.config import get_config
from local_server.routers.status import is_strategy_running

logger = logging.getLogger(__name__)

# 연속 실패 임계값 (interval 기준)
_WARN_THRESHOLD = 10   # 10 * 30s = 5분
_ERROR_THRESHOLD = 60  # 60 * 30s = 30분


def _build_heartbeat_payload() -> dict[str, Any]:
    """현재 로컬 서버 상태를 담은 하트비트 페이로드를 생성한다."""
    return {
        "status": "online",
        "strategy_engine": "running" if is_strategy_running() else "stopped",
    }


async def start_heartbeat() -> None:
    """하트비트 전송 루프를 실행한다.

    응답에서 rules_version, context_version 변경을 감지하면
    해당 데이터를 자동으로 fetch하여 로컬 캐시를 갱신한다.
    """
    cfg = get_config()
    cloud_url = cfg.get("cloud.url", "")
    interval = cfg.get("cloud.heartbeat_interval", 30)

    if not cloud_url:
        logger.warning("cloud.url이 설정되지 않아 하트비트를 시작할 수 없습니다.")
        return

    client = CloudClient(base_url=cloud_url)
    logger.info("하트비트 시작: 간격=%ds, 대상=%s", interval, cloud_url)

    last_rules_version: str | None = None
    last_context_version: str | None = None
    last_watchlist_version: str | None = None
    last_stock_master_version: str | None = None
    consecutive_failures = 0

    while True:
        try:
            payload = _build_heartbeat_payload()
            resp = await client.send_heartbeat(payload)
            logger.debug("하트비트 전송 완료")

            # 버전 감지 → 자동 fetch
            await _check_version_changes(
                client, resp,
                last_rules_version, last_context_version,
                last_watchlist_version, last_stock_master_version,
            )

            # 버전 갱신
            if resp.get("rules_version") is not None:
                last_rules_version = resp["rules_version"]
            if resp.get("context_version") is not None:
                last_context_version = resp["context_version"]
            if resp.get("watchlist_version") is not None:
                last_watchlist_version = resp["watchlist_version"]
            if resp.get("stock_master_version") is not None:
                last_stock_master_version = resp["stock_master_version"]

            # 성공 → 실패 카운터 리셋 + 트레이 초록
            if consecutive_failures > 0:
                consecutive_failures = 0
                _update_tray("ok")

        except CloudClientError as e:
            consecutive_failures += 1
            logger.warning("하트비트 전송 실패 (%d연속): %s", consecutive_failures, e)
            _handle_failure(consecutive_failures)

        except asyncio.CancelledError:
            logger.info("하트비트 루프 종료")
            break

        except Exception as e:
            consecutive_failures += 1
            logger.error("하트비트 예상치 못한 오류 (%d연속): %s", consecutive_failures, e)
            _handle_failure(consecutive_failures)

        await asyncio.sleep(interval)


async def _check_version_changes(
    client: CloudClient,
    resp: dict[str, Any],
    last_rules_ver: str | None,
    last_context_ver: str | None,
    last_watchlist_ver: str | None,
    last_stock_master_ver: str | None,
) -> None:
    """하트비트 응답에서 버전 변경을 감지하여 fetch를 트리거한다."""
    rules_ver = resp.get("rules_version")
    if rules_ver is not None and rules_ver != last_rules_ver:
        logger.info("규칙 버전 변경 감지: %s → %s", last_rules_ver, rules_ver)
        try:
            rules = await client.fetch_rules()
            from local_server.storage.rules_cache import get_rules_cache
            get_rules_cache().sync(rules)
        except Exception as e:
            logger.error("규칙 자동 fetch 실패: %s", e)

    context_ver = resp.get("context_version")
    if context_ver is not None and context_ver != last_context_ver:
        logger.info("컨텍스트 버전 변경 감지: %s → %s", last_context_ver, context_ver)
        try:
            from local_server.cloud.context import fetch_and_cache_context
            await fetch_and_cache_context(client)
        except Exception as e:
            logger.error("컨텍스트 자동 fetch 실패: %s", e)

    watchlist_ver = resp.get("watchlist_version")
    if watchlist_ver is not None and watchlist_ver != last_watchlist_ver:
        logger.info("관심종목 버전 변경 감지: %s → %s", last_watchlist_ver, watchlist_ver)
        try:
            data = await client._get("/api/watchlist")
            items = data.get("data", []) if isinstance(data, dict) else []
            from local_server.storage.watchlist_cache import get_watchlist_cache
            get_watchlist_cache().sync(items)
        except Exception as e:
            logger.error("관심종목 자동 fetch 실패: %s", e)

    stock_ver = resp.get("stock_master_version")
    if stock_ver is not None and stock_ver != last_stock_master_ver:
        logger.info("종목 마스터 버전 변경 감지: %s → %s", last_stock_master_ver, stock_ver)
        try:
            data = await client._get("/api/stocks/master")
            stocks = data.get("data", []) if isinstance(data, dict) else []
            from local_server.storage.stock_master_cache import get_stock_master_cache
            get_stock_master_cache().sync(stocks)
        except Exception as e:
            logger.error("종목 마스터 자동 fetch 실패: %s", e)


def _handle_failure(consecutive_failures: int) -> None:
    """연속 실패 횟수에 따라 트레이 상태를 전환한다."""
    if consecutive_failures >= _ERROR_THRESHOLD:
        _update_tray("error")
        if consecutive_failures == _ERROR_THRESHOLD:
            _send_toast("StockVision 연결 오류", "클라우드 서버와 30분 이상 연결할 수 없습니다.")
    elif consecutive_failures >= _WARN_THRESHOLD:
        _update_tray("warning")


def _update_tray(status: str) -> None:
    """트레이 아이콘 상태를 갱신한다."""
    try:
        from local_server.tray.tray_app import update_tray_status
        update_tray_status(status)  # type: ignore[arg-type]
    except Exception:
        pass


def _send_toast(title: str, message: str) -> None:
    """Windows 토스트 알림을 전송한다."""
    try:
        from local_server.utils.toast import show_toast
        show_toast(title, message)
    except Exception:
        pass
