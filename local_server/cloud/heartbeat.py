"""클라우드 하트비트 전송 모듈.

설정된 간격으로 클라우드 서버에 로컬 서버 상태를 전송한다.
하트비트 응답에서 버전 변경을 감지하여 규칙/컨텍스트를 자동 fetch한다.
연속 실패 시 트레이 아이콘 색상을 변경한다 (5분→🟡, 30분→🔴).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from local_server.__version__ import __version__ as _VERSION
from local_server.cloud.client import CloudClient, CloudClientError
from local_server.cloud.ws_relay_client import get_ws_relay_client
from local_server.config import get_config

logger = logging.getLogger(__name__)

# 연속 실패 임계값 (interval 기준)
_WARN_THRESHOLD = 10   # 10 * 30s = 5분
_ERROR_THRESHOLD = 60  # 60 * 30s = 30분

# 엔진 상태 — main.py lifespan에서 갱신
_engine_running = False

# CloudClient 싱글턴 — 하트비트 루프에서 생성, 외부에서 참조 가능
_client: CloudClient | None = None


def get_cloud_client() -> CloudClient | None:
    """하트비트가 사용하는 CloudClient 인스턴스를 반환한다."""
    return _client


def set_engine_running(running: bool) -> None:
    """엔진 실행 상태를 갱신한다. 엔진 시작/중지 시 호출."""
    global _engine_running
    _engine_running = running


def _build_heartbeat_payload() -> dict[str, Any]:
    """현재 로컬 서버 상태를 담은 하트비트 페이로드를 생성한다.

    서버 HeartbeatBody 스키마에 맞춰 uuid, timestamp, engine_running 등을 전송한다.
    """
    from datetime import datetime, timezone
    import platform
    cfg = get_config()

    # UUID: 최초 생성 후 config에 저장
    uuid = cfg.get("server.uuid")
    if not uuid:
        from uuid import uuid4
        uuid = str(uuid4())
        cfg.set("server.uuid", uuid)
        cfg.save()

    return {
        "uuid": uuid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_running": _engine_running,
        "version": _VERSION,
        "os": platform.system(),
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

    global _client
    from local_server.storage.credential import load_cloud_tokens
    access_token, _ = load_cloud_tokens()
    _client = CloudClient(base_url=cloud_url, api_token=access_token)
    client = _client
    logger.info("하트비트 시작: 간격=%ds, 대상=%s", interval, cloud_url)

    last_rules_version: str | None = None
    last_context_version: str | None = None
    last_watchlist_version: str | None = None
    last_stock_master_version: str | None = None
    consecutive_failures = 0

    # R4: WS heartbeat_ack에서 버전 변경을 감지하는 콜백
    async def _on_heartbeat_ack(ack_payload: dict) -> None:
        nonlocal last_rules_version, last_context_version
        nonlocal last_watchlist_version, last_stock_master_version

        await _check_version_changes(
            client, ack_payload,
            last_rules_version, last_context_version,
            last_watchlist_version, last_stock_master_version,
        )
        _check_server_version(ack_payload)

        if ack_payload.get("rules_version") is not None:
            last_rules_version = str(ack_payload["rules_version"])
        if ack_payload.get("context_version") is not None:
            last_context_version = str(ack_payload["context_version"])
        if ack_payload.get("watchlist_version") is not None:
            last_watchlist_version = str(ack_payload["watchlist_version"])
        if ack_payload.get("stock_master_version") is not None:
            last_stock_master_version = str(ack_payload["stock_master_version"])

    # WS 클라이언트에 ack 핸들러 등록
    ws_client_init = get_ws_relay_client()
    if ws_client_init:
        ws_client_init.set_heartbeat_ack_handler(_on_heartbeat_ack)

    while True:
        try:
            payload = _build_heartbeat_payload()

            # WS 우선, HTTP 폴백
            ws_client = get_ws_relay_client()
            if ws_client and ws_client.is_connected:
                await ws_client.send_heartbeat(payload)
                logger.debug("하트비트 전송 완료 (WS)")
                # R4: heartbeat_ack는 WS _on_heartbeat_ack 콜백에서 버전 체크 수행
                resp = None
            else:
                resp = await client.send_heartbeat(payload)
                logger.debug("하트비트 전송 완료 (HTTP 폴백)")

            if resp:
                # 버전 감지 → 자동 fetch
                await _check_version_changes(
                    client, resp,
                    last_rules_version, last_context_version,
                    last_watchlist_version, last_stock_master_version,
                )

                # 서버 버전 업데이트 알림
                _check_server_version(resp)

                # 버전 갱신 (cloud가 int를 보내도 str로 통일)
                if resp.get("rules_version") is not None:
                    last_rules_version = str(resp["rules_version"])
                if resp.get("context_version") is not None:
                    last_context_version = str(resp["context_version"])
                if resp.get("watchlist_version") is not None:
                    last_watchlist_version = str(resp["watchlist_version"])
                if resp.get("stock_master_version") is not None:
                    last_stock_master_version = str(resp["stock_master_version"])

            # 성공 → 실패 카운터 리셋 + 트레이 초록 + SyncQueue flush
            if consecutive_failures > 0:
                consecutive_failures = 0
                _update_tray("ok")
                await _flush_sync_queue(client)

        except CloudClientError as e:
            if e.status_code == 401:
                refreshed = await _try_refresh(client)
                if refreshed:
                    consecutive_failures = 0
                    continue  # 갱신 후 즉시 재시도
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


_version_notified: str | None = None  # 이미 알림 보낸 버전


def _check_server_version(resp: dict[str, Any]) -> None:
    """하트비트 응답에서 최신/최소 버전을 확인하여 토스트 알림을 보낸다."""
    global _version_notified

    latest = resp.get("latest_version")
    min_ver = resp.get("min_version")
    if not latest:
        return

    current = _VERSION

    if current == latest or _version_notified == latest:
        return

    try:
        from packaging.version import Version
        cur_v = Version(current)
        latest_v = Version(latest)
        min_v = Version(min_ver) if min_ver else None
    except Exception:
        return

    if cur_v >= latest_v:
        return

    _version_notified = latest
    download_url = resp.get("download_url", "")

    if min_v and cur_v < min_v:
        _send_toast(
            "StockVision 업데이트 필수",
            f"현재 버전({current})은 더 이상 지원되지 않습니다. {latest}로 업데이트하세요.",
        )
        logger.warning("서버 버전 %s → 최소 지원 %s 미달", current, min_ver)
    else:
        _send_toast(
            "StockVision 업데이트 가능",
            f"새 버전 {latest}이 있습니다. (현재: {current})",
        )
        logger.info("새 버전 사용 가능: %s → %s", current, latest)


async def _check_version_changes(
    client: CloudClient,
    resp: dict[str, Any],
    last_rules_ver: str | None,
    last_context_ver: str | None,
    last_watchlist_ver: str | None,
    last_stock_master_ver: str | None,
) -> None:
    """하트비트 응답에서 버전 변경을 감지하여 fetch를 트리거한다."""
    rules_ver = str(resp["rules_version"]) if resp.get("rules_version") is not None else None
    if rules_ver is not None and rules_ver != last_rules_ver:
        logger.info("규칙 버전 변경 감지: %s → %s", last_rules_ver, rules_ver)
        try:
            rules = await client.fetch_rules()
            from local_server.storage.rules_cache import get_rules_cache
            get_rules_cache().sync(rules)
        except Exception as e:
            logger.error("규칙 자동 fetch 실패: %s", e)

    context_ver = str(resp["context_version"]) if resp.get("context_version") is not None else None
    if context_ver is not None and context_ver != last_context_ver:
        logger.info("컨텍스트 버전 변경 감지: %s → %s", last_context_ver, context_ver)
        try:
            from local_server.cloud.context import fetch_and_cache_context
            await fetch_and_cache_context(client)
        except Exception as e:
            logger.error("컨텍스트 자동 fetch 실패: %s", e)

    watchlist_ver = str(resp["watchlist_version"]) if resp.get("watchlist_version") is not None else None
    if watchlist_ver is not None and watchlist_ver != last_watchlist_ver:
        logger.info("관심종목 버전 변경 감지: %s → %s", last_watchlist_ver, watchlist_ver)
        try:
            data = await client._get("/api/watchlist")
            items = data.get("data", []) if isinstance(data, dict) else []
            from local_server.storage.watchlist_cache import get_watchlist_cache
            get_watchlist_cache().sync(items)
        except Exception as e:
            logger.error("관심종목 자동 fetch 실패: %s", e)

    stock_ver = str(resp["stock_master_version"]) if resp.get("stock_master_version") is not None else None
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


async def _try_refresh(client: CloudClient) -> bool:
    """401 발생 시 refresh_token으로 토큰 갱신. _refresh_lock으로 교차 경쟁 방지."""
    from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired
    from local_server.storage.credential import load_cloud_tokens, save_cloud_tokens
    async with _refresh_lock:
        access_token, refresh_token = load_cloud_tokens()
        if access_token and not is_jwt_expired(access_token):
            # 선행 요청이 이미 refresh함 → 새 토큰 사용
            client.set_token(access_token)
            return True
        if not refresh_token:
            return False
        try:
            tokens = await client.refresh_access_token(refresh_token)
            client.set_token(tokens["access_token"])
            save_cloud_tokens(tokens["access_token"], tokens["refresh_token"])
            logger.info("하트비트 토큰 자동 갱신 완료")
            return True
        except CloudClientError:
            _update_tray("error")
            _send_toast("StockVision", "재로그인이 필요합니다.")
            return False


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


async def _flush_sync_queue(client: CloudClient) -> None:
    """연결 복구 시 오프라인 큐를 순서대로 플러시한다."""
    from local_server.storage.sync_queue import get_sync_queue
    queue = get_sync_queue()
    if queue.is_empty():
        return

    flushed = 0
    while not queue.is_empty():
        items = queue.peek_all()
        if not items:
            break
        item = items[0]
        try:
            action = item.get("type", "")
            if action.startswith("rule_"):
                await client.fetch_rules()  # 서버 규칙으로 덮어쓰기 (last-write-wins)
            queue.dequeue()
            flushed += 1
        except Exception:
            logger.error("SyncQueue flush 실패 — 재시도 보류 (%d건 잔여)", queue.count())
            break

    if flushed:
        logger.info("SyncQueue flush 완료: %d건 처리", flushed)
