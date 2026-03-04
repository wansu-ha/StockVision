"""
설정 관리자

- 클라우드에서 받은 설정을 메모리에 보관
- 변경 시 500ms debounce 후 클라우드 업로드
- 규칙(TradingRule) 활성화/비활성화 제어
"""
import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 0.5


class ConfigManager:
    def __init__(self):
        self._config: dict = {}
        self._jwt: str | None = None
        self._lock = threading.Lock()
        self._debounce_task: asyncio.Task | None = None

    # ── 로드 ──────────────────────────────────────────────────

    def load(self, config: dict, jwt: str | None = None) -> None:
        """클라우드에서 받은 설정 전체 교체"""
        with self._lock:
            self._config = config
            if jwt:
                self._jwt = jwt
        logger.info(f"설정 로드 완료: {len(config)} 키")

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def get_all(self) -> dict:
        with self._lock:
            return dict(self._config)

    # ── 업데이트 ──────────────────────────────────────────────

    def update(self, patch: dict) -> None:
        """부분 업데이트 후 클라우드 업로드 (debounce)"""
        with self._lock:
            self._config.update(patch)
        self._schedule_upload()

    def set_rule_active(self, rule_id: int, is_active: bool) -> None:
        rules = self.get("rules", [])
        for rule in rules:
            if rule.get("id") == rule_id:
                rule["is_active"] = is_active
                break
        with self._lock:
            self._config["rules"] = rules
        self._schedule_upload()

    def get_active_rules(self) -> list:
        return [r for r in self.get("rules", []) if r.get("is_active")]

    def set_jwt(self, jwt: str) -> None:
        with self._lock:
            self._jwt = jwt

    # ── 클라우드 업로드 ───────────────────────────────────────

    def _schedule_upload(self) -> None:
        """이벤트 루프가 있으면 debounce 업로드 예약"""
        try:
            loop = asyncio.get_running_loop()
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()
            self._debounce_task = loop.create_task(self._upload_after_debounce())
        except RuntimeError:
            pass  # 이벤트 루프 없음 (테스트 등)

    async def _upload_after_debounce(self) -> None:
        await asyncio.sleep(_DEBOUNCE_SECONDS)
        await self._upload()

    async def _upload(self) -> None:
        import httpx
        jwt = self._jwt
        if not jwt:
            logger.warning("JWT 없음 — 클라우드 업로드 스킵")
            return
        import os
        cloud_url = os.environ.get("CLOUD_URL", "https://stockvision.app")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{cloud_url}/api/v1/config",
                    json=self.get_all(),
                    headers={"Authorization": f"Bearer {jwt}"},
                    timeout=10,
                )
            if resp.status_code == 401:
                logger.warning("JWT 만료 — 설정 업로드 실패 (재로그인 필요)")
            else:
                resp.raise_for_status()
                logger.info("설정 클라우드 업로드 완료")
        except Exception as e:
            logger.error(f"설정 업로드 오류: {e}")


_config_manager: ConfigManager | None = None


def set_config_manager(cm: ConfigManager) -> None:
    global _config_manager
    _config_manager = cm


def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
