"""
시장 컨텍스트 fetch + 로컬 파일 캐시

- 장 마감 후 1회 fetch → %APPDATA%/StockVision/context_cache.json 저장
- 전략 평가 엔진은 get_context()로 캐시 참조 (실시간 아님)
- 클라우드 오류 시 이전 캐시 유지
"""
import json
import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CLOUD_URL  = os.environ.get("CLOUD_URL", "https://stockvision.app")
_CACHE_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "StockVision"
_CACHE_FILE = _CACHE_DIR / "context_cache.json"
_MEM_TTL    = 300  # 메모리 캐시 5분

_mem_cache: dict = {}
_mem_cache_time: float = 0.0


def fetch_and_cache(jwt: str) -> None:
    """클라우드에서 컨텍스트 가져와 파일에 저장 (장 마감 후 호출)"""
    global _mem_cache, _mem_cache_time
    try:
        resp = httpx.get(
            f"{_CLOUD_URL}/api/context",
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        _mem_cache      = data
        _mem_cache_time = time.time()
        logger.info("시장 컨텍스트 캐시 갱신 완료")
    except Exception as e:
        logger.warning(f"컨텍스트 fetch 실패 (이전 캐시 유지): {e}")


def get_context() -> dict:
    """캐시된 컨텍스트 반환 — 메모리 → 파일 순서로 조회"""
    global _mem_cache, _mem_cache_time
    if time.time() - _mem_cache_time < _MEM_TTL and _mem_cache:
        return _mem_cache
    if _CACHE_FILE.exists():
        try:
            _mem_cache      = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            _mem_cache_time = time.time()
        except Exception as e:
            logger.warning(f"컨텍스트 캐시 파일 읽기 실패: {e}")
    return _mem_cache
