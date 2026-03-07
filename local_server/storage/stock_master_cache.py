"""종목 메타데이터 JSON 캐시 저장소.

클라우드 서버에서 전체 종목 마스터를 받아 stock_master.json에 캐시한다.
오프라인에서도 종목 검색이 가능하도록 한다 (~150KB).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MASTER_PATH = Path.home() / ".stockvision" / "stock_master.json"
DEFAULT_DETAIL_PATH = Path.home() / ".stockvision" / "stock_detail_cache.json"


class StockMasterCache:
    """종목 마스터 + 상세 캐시."""

    def __init__(
        self,
        master_path: Path | None = None,
        detail_path: Path | None = None,
    ) -> None:
        self._master_path = master_path or DEFAULT_MASTER_PATH
        self._detail_path = detail_path or DEFAULT_DETAIL_PATH
        self._stocks: list[dict[str, Any]] = []
        self._details: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        self._stocks = self._load_json(self._master_path, expected_type=list) or []
        self._details = self._load_json(self._detail_path, expected_type=dict) or {}
        if self._stocks:
            logger.info("종목 마스터 캐시 로드: %d개", len(self._stocks))

    @staticmethod
    def _load_json(path: Path, expected_type: type) -> Any:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, expected_type) else None
        except (json.JSONDecodeError, OSError) as e:
            logger.error("캐시 로드 실패 (%s): %s", path.name, e)
            return None

    def _save_master(self) -> None:
        self._master_path.parent.mkdir(parents=True, exist_ok=True)
        with self._master_path.open("w", encoding="utf-8") as f:
            json.dump(self._stocks, f, ensure_ascii=False, indent=2)

    def _save_details(self) -> None:
        self._detail_path.parent.mkdir(parents=True, exist_ok=True)
        with self._detail_path.open("w", encoding="utf-8") as f:
            json.dump(self._details, f, ensure_ascii=False, indent=2)

    # ── 마스터 ──

    def sync(self, stocks: list[dict[str, Any]]) -> None:
        """클라우드에서 받은 종목 마스터로 전량 교체한다."""
        self._stocks = list(stocks)
        self._save_master()
        logger.info("종목 마스터 동기화: %d개", len(self._stocks))

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._stocks)

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """종목 코드 또는 이름으로 검색한다 (로컬 캐시 기반)."""
        q = query.strip().lower()
        if not q:
            return []
        results = []
        for stock in self._stocks:
            symbol = stock.get("symbol", "").lower()
            name = stock.get("name", "").lower()
            if q in symbol or q in name:
                results.append(stock)
                if len(results) >= limit:
                    break
        return results

    def count(self) -> int:
        return len(self._stocks)

    # ── 상세 (온디맨드 캐시) ──

    def get_detail(self, symbol: str) -> dict[str, Any] | None:
        return self._details.get(symbol)

    def set_detail(self, symbol: str, detail: dict[str, Any]) -> None:
        """조회한 종목 상세를 캐시에 저장한다."""
        self._details[symbol] = detail
        self._save_details()


_instance: StockMasterCache | None = None


def get_stock_master_cache() -> StockMasterCache:
    global _instance
    if _instance is None:
        _instance = StockMasterCache()
    return _instance
