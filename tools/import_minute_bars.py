"""분봉 JSON 파일을 cloud DB MinuteBar 테이블에 임포트.

kiwoom_minute_batch.py 또는 creon_collector.py가 생성한 JSON 파일을
PostgreSQL/SQLite MinuteBar 테이블에 bulk upsert한다.

사용법:
    python -m tools.import_minute_bars data/minute_bars/005930_1m.json
    python -m tools.import_minute_bars data/minute_bars/  # 디렉토리 전체
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# cloud_server 환경변수 설정
import os
os.environ.setdefault("SECRET_KEY", "import-tool-secret")

from cloud_server.core.database import engine, Base, SessionLocal
from cloud_server.models.market import MinuteBar

logger = logging.getLogger(__name__)


def import_file(filepath: Path, db_session) -> int:
    """단일 JSON 파일을 DB에 임포트. 반환: upsert 건수."""
    # 파일명에서 종목코드 추출: 005930_1m.json → 005930
    symbol = filepath.stem.split("_")[0]

    with open(filepath, "r", encoding="utf-8") as f:
        bars = json.load(f)

    if not bars:
        logger.warning("빈 파일: %s", filepath)
        return 0

    count = 0
    for bar in bars:
        ts_str = bar.get("timestamp", "")
        if not ts_str:
            continue

        # 타임스탬프 파싱 (여러 포맷 지원)
        ts = _parse_timestamp(ts_str)
        if ts is None:
            continue

        # 분 경계로 정렬
        ts = ts.replace(second=0, microsecond=0)

        existing = db_session.query(MinuteBar).filter(
            MinuteBar.symbol == symbol,
            MinuteBar.timestamp == ts,
        ).first()

        if existing:
            # upsert: OHLCV 갱신
            existing.open = bar.get("open") or existing.open
            existing.high = max(existing.high or 0, bar.get("high", 0))
            existing.low = min(existing.low or 999999999, bar.get("low", 999999999))
            existing.close = bar.get("close") or existing.close
            existing.volume = bar.get("volume") or existing.volume
        else:
            db_session.add(MinuteBar(
                symbol=symbol,
                timestamp=ts,
                open=bar.get("open"),
                high=bar.get("high"),
                low=bar.get("low"),
                close=bar.get("close"),
                volume=bar.get("volume"),
            ))
        count += 1

    db_session.commit()
    return count


def _parse_timestamp(ts_str: str) -> datetime | None:
    """여러 포맷의 타임스탬프를 파싱."""
    for fmt in (
        "%Y%m%d%H%M%S",    # 20250301093000
        "%Y-%m-%dT%H:%M:%S",  # ISO
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d%H%M",       # 202503010930
    ):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="분봉 JSON → DB 임포트")
    parser.add_argument("path", help="JSON 파일 또는 디렉토리 경로")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    target = Path(args.path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("*.json"))
    else:
        print(f"ERROR: {target} 존재하지 않음")
        sys.exit(1)

    if not files:
        print("임포트할 JSON 파일 없음")
        sys.exit(0)

    # DB 테이블 확인
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    total = 0
    try:
        for f in files:
            count = import_file(f, db)
            logger.info("%s: %d건 임포트", f.name, count)
            total += count
    finally:
        db.close()

    logger.info("=== 총 %d건 임포트 완료 (%d파일) ===", total, len(files))


if __name__ == "__main__":
    main()
