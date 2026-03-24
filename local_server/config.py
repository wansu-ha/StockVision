"""로컬 서버 설정 모듈.

config.json을 읽어 설정을 로드하고,
런타임에 설정을 변경하여 저장한다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


# 기본 설정 파일 경로
DEFAULT_CONFIG_PATH = Path.home() / ".stockvision" / "config.json"

# 기본 설정값
DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 4020,
    },
    "cloud": {
        "url": "",           # 클라우드 서버 URL (비어있으면 클라우드 연동 비활성화)
        "ws_url": "",        # 클라우드 WS URL (비어있으면 cloud.url에서 자동 생성)
        "heartbeat_interval": 30,  # 하트비트 전송 간격 (초)
    },
    "broker": {
        "type": "kiwoom",    # "kis" | "kiwoom" | "mock"
        "is_mock": True,     # 모의투자 여부
    },
    "kis": {
        "account_no": "",    # 한국투자증권 계좌번호 (앱 키/시크릿은 keyring 전용)
    },
    "budget_ratio": 10,         # 예산 비율 (%)
    "max_positions": 5,          # 최대 보유 종목 수
    "max_loss_pct": 5.0,         # 최대 손실률 (%)
    "max_orders_per_minute": 10, # 분당 최대 주문 수
    "cors": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://stock-vision-two.vercel.app",
        ],
    },
    "sleep_prevent": True,   # Windows 수면 방지 활성화 여부
    "log_level": "INFO",
    "alerts": {
        "master_enabled": True,
        "rules": {
            "position_loss":        {"enabled": True,  "threshold_pct": -3.0},
            "volatility":           {"enabled": True,  "threshold_pct": 5.0},
            "stale_order":          {"enabled": True,  "threshold_min": 10},
            "daily_loss_proximity": {"enabled": True},
            "market_close_orders":  {"enabled": True},
            "engine_health":        {"enabled": True},
            "broker_health":        {"enabled": True},
            "kill_switch":          {"enabled": True},
            "loss_lock":            {"enabled": True},
        },
    },
}


class Config:
    """설정 관리 클래스."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or Path(
            os.environ.get("SV_CONFIG_PATH", str(DEFAULT_CONFIG_PATH))
        )
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """파일에서 설정을 로드한다. 파일이 없으면 기본값을 사용한다."""
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 기본값 위에 로드된 값을 덮어씀 (중첩 딕셔너리 병합)
            self._data = self._merge(DEFAULT_CONFIG, loaded)
        else:
            self._data = dict(DEFAULT_CONFIG)

    def _merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """중첩 딕셔너리를 재귀적으로 병합한다."""
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self) -> None:
        """현재 설정을 파일에 atomic write로 저장한다.

        임시 파일에 먼저 쓴 후 os.replace()로 교체하여
        동시 호출이나 쓰기 중 프로세스 종료 시에도 파일 손상을 방지한다.
        """
        import contextlib
        import tempfile

        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._path.parent),
            suffix=".tmp",
            prefix=".config-",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(self._path))
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """점 표기법으로 설정값을 가져온다 (예: 'server.port')."""
        current: Any = self._data
        parts = key.split(".")
        for part in parts:
            if not isinstance(current, dict):
                return default
            current = current.get(part)
            if current is None:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """점 표기법으로 설정값을 변경한다."""
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        """전체 설정을 딕셔너리로 반환한다."""
        return dict(self._data)

    def update(self, updates: dict[str, Any]) -> None:
        """딕셔너리로 설정을 일괄 업데이트한다."""
        self._data = self._merge(self._data, updates)


# 전역 싱글턴 설정 인스턴스
_config_instance: Config | None = None


def get_config() -> Config:
    """전역 설정 인스턴스를 반환한다."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
