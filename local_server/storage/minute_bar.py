"""로컬 SQLite 분봉 저장소.

1분봉 저장/조회/정리 + 5분/15분/시봉 집계.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".stockvision" / "minute_bars.db"


class MinuteBarStore:
    """로컬 SQLite 분봉 저장소."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS minute_bars (
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    PRIMARY KEY (symbol, timestamp)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def save_bars(self, symbol: str, bars: list[dict]) -> int:
        """분봉 목록 upsert. 저장 건수 반환."""
        if not bars:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO minute_bars
                   (symbol, timestamp, open, high, low, close, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (symbol, b["time"], b.get("open"), b.get("high"),
                     b.get("low"), b.get("close"), b.get("volume"))
                    for b in bars
                ],
            )
        return len(bars)

    def get_bars(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        """기간 내 1분봉 조회."""
        query = "SELECT timestamp, open, high, low, close, volume FROM minute_bars WHERE symbol = ?"
        params: list[Any] = [symbol]
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        query += " ORDER BY timestamp"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {"time": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
            for r in rows
        ]

    def get_range(self, symbol: str) -> tuple[str, str] | None:
        """저장된 데이터 범위 반환."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM minute_bars WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        if row and row[0]:
            return (row[0], row[1])
        return None

    def purge_old(self, days: int = 30) -> int:
        """N일 이전 데이터 삭제."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM minute_bars WHERE timestamp < ?", (cutoff,)
            )
        count = cursor.rowcount
        if count:
            logger.info("분봉 정리: %d건 삭제 (>%d일)", count, days)
        return count


def aggregate_bars(bars_1m: list[dict], resolution: str) -> list[dict]:
    """1분봉 리스트를 지정 해상도로 집계.

    resolution: '5m' | '15m' | '1h'
    """
    if not bars_1m:
        return []

    minutes = {"5m": 5, "15m": 15, "1h": 60}.get(resolution)
    if not minutes:
        return bars_1m  # 1m은 그대로

    result: list[dict] = []
    bucket: list[dict] = []

    for bar in bars_1m:
        ts = bar["time"]
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue

        # 구간 시작 기준: 분 단위로 나눈 몫
        bucket_start_min = (dt.hour * 60 + dt.minute) // minutes * minutes
        bucket_start = dt.replace(
            hour=bucket_start_min // 60,
            minute=bucket_start_min % 60,
            second=0, microsecond=0,
        )

        if bucket and bucket[0]["_bucket"] != bucket_start:
            result.append(_merge_bucket(bucket))
            bucket = []

        bar_copy = dict(bar)
        bar_copy["_bucket"] = bucket_start
        bucket.append(bar_copy)

    if bucket:
        result.append(_merge_bucket(bucket))

    return result


def _merge_bucket(bucket: list[dict]) -> dict:
    """봉 그룹을 하나의 봉으로 합산."""
    return {
        "time": bucket[0]["_bucket"].isoformat(),
        "open": bucket[0].get("open"),
        "high": max((b.get("high") or 0) for b in bucket),
        "low": min((b.get("low") or float("inf")) for b in bucket),
        "close": bucket[-1].get("close"),
        "volume": sum((b.get("volume") or 0) for b in bucket),
    }


_instance: MinuteBarStore | None = None


def get_minute_bar_store() -> MinuteBarStore:
    global _instance
    if _instance is None:
        _instance = MinuteBarStore()
    return _instance
