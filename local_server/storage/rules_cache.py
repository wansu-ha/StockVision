"""매매 규칙 JSON 캐시 저장소.

클라우드 서버에서 동기화된 매매 규칙을 로컬 rules.json에 캐시한다.
네트워크 단절 시에도 마지막으로 동기화된 규칙으로 전략 엔진이 동작할 수 있다.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 기본 캐시 파일 경로
DEFAULT_RULES_PATH = Path.home() / ".stockvision" / "rules.json"


class RulesCache:
    """매매 규칙 JSON 캐시."""

    def __init__(self, rules_path: Path | None = None) -> None:
        self._path = rules_path or DEFAULT_RULES_PATH
        self._rules: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """파일에서 규칙을 로드한다. 파일이 없으면 빈 목록으로 시작한다."""
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self._rules = data if isinstance(data, list) else []
                logger.info("규칙 캐시 로드: %d개", len(self._rules))
            except (json.JSONDecodeError, OSError) as e:
                logger.error("규칙 캐시 로드 실패: %s", e)
                self._rules = []
        else:
            self._rules = []

    def _save(self) -> None:
        """규칙을 파일에 저장한다."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._rules, f, ensure_ascii=False, indent=2)
        logger.debug("규칙 캐시 저장: %d개", len(self._rules))

    def get_rules(self) -> list[dict[str, Any]]:
        """현재 캐시된 규칙 목록을 반환한다."""
        return list(self._rules)

    def sync(self, rules: list[dict[str, Any]]) -> None:
        """클라우드에서 받은 규칙으로 캐시를 전량 교체한다."""
        self._rules = list(rules)
        self._save()
        logger.info("규칙 캐시 동기화 완료: %d개", len(self._rules))

    def count(self) -> int:
        """캐시된 규칙 수를 반환한다."""
        return len(self._rules)


# 전역 싱글턴
_rules_cache_instance: RulesCache | None = None


def get_rules_cache() -> RulesCache:
    """전역 규칙 캐시 인스턴스를 반환한다."""
    global _rules_cache_instance
    if _rules_cache_instance is None:
        _rules_cache_instance = RulesCache()
    return _rules_cache_instance
