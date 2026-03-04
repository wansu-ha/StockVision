"""
키움 연결 상태 관리

- COM 연결 위임 → KiwoomCOMClient
- 재연결: 최대 3회, 지수 백오프 (5s / 10s / 15s)
- 재연결 실패 시: 트레이 알림 + 스케줄러 일시정지 + WS 브로드캐스트
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class KiwoomSession:
    def __init__(self):
        self.connected = False
        self.mode: str = "none"  # "demo" | "real" | "none"

    # ── 연결 ──────────────────────────────────────────────────

    def connect(self) -> bool:
        """COM 연결 시도 (HTS 로그인 상태 필요)"""
        from kiwoom.com_client import get_client
        client = get_client()
        ok = client.connect()
        if ok:
            self.connected = True
            self.mode = self._detect_mode(client)
            logger.info(f"키움 연결 성공 — 모드: {self.mode}")
        return ok

    def reconnect(self, max_retries: int = 3) -> bool:
        """지수 백오프 재연결 (5s → 10s → 15s)"""
        for attempt in range(1, max_retries + 1):
            logger.info(f"재연결 시도 {attempt}/{max_retries}")
            if self.connect():
                return True
            wait = 5 * attempt
            logger.warning(f"재연결 실패 — {wait}s 후 재시도")
            time.sleep(wait)
        self._on_reconnect_failed()
        return False

    def disconnect(self) -> None:
        self.connected = False
        self.mode = "none"
        logger.info("키움 연결 해제")

    # ── 상태 ──────────────────────────────────────────────────

    def status(self) -> dict:
        """실시간 연결 상태 반환 (COM GetConnectState 기반)"""
        from kiwoom.com_client import get_client
        live = get_client().is_connected()
        if self.connected and not live:
            # 예상치 못한 단절 감지
            logger.warning("키움 연결 단절 감지 — 재연결 시도")
            self.connected = False
            asyncio.create_task(self._async_reconnect())
        return {"connected": live, "mode": self.mode}

    # ── 내부 ──────────────────────────────────────────────────

    def _detect_mode(self, client) -> str:
        """GetServerGubun: 0=실계좌, 1=모의투자"""
        raw = client.get_login_info("GetServerGubun")
        return "demo" if raw.strip() == "1" else "real"

    def _on_reconnect_failed(self) -> None:
        """재연결 완전 실패 — 알림 + 스케줄러 정지"""
        self.connected = False
        self.mode = "none"
        logger.error("키움 재연결 최종 실패")

        # 트레이 알림
        try:
            from tray import notify
            notify("키움 연결 실패", "재연결에 실패했습니다. HTS 상태를 확인하세요.")
        except Exception:
            pass

        # 스케줄러 일시정지
        try:
            from engine.scheduler import get_scheduler
            get_scheduler().pause()
        except Exception:
            pass

        # WS 브로드캐스트
        asyncio.create_task(self._broadcast_disconnect())

    async def _async_reconnect(self) -> None:
        await asyncio.sleep(3)  # 짧은 대기 후 재연결
        self.reconnect()

    async def _broadcast_disconnect(self) -> None:
        try:
            from routers.ws import broadcast
            await broadcast({"type": "kiwoom_disconnected", "data": {}})
        except Exception:
            pass


_session = KiwoomSession()


def get_session() -> KiwoomSession:
    return _session
