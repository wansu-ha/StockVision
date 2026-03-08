"""체결/에러 로그 SQLite 저장소.

SQLite(logs.db)에 구조화된 로그를 저장하고 조회한다.
비동기 I/O를 위해 aiosqlite를 사용한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 기본 DB 파일 경로
DEFAULT_LOG_DB_PATH = Path.home() / ".stockvision" / "logs.db"

# 로그 종류 상수
LOG_TYPE_FILL = "FILL"         # 체결
LOG_TYPE_ORDER = "ORDER"       # 주문
LOG_TYPE_ERROR = "ERROR"       # 에러
LOG_TYPE_SYSTEM = "SYSTEM"     # 시스템 이벤트
LOG_TYPE_STRATEGY = "STRATEGY" # 전략 엔진 이벤트

# DDL
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT    NOT NULL,
    log_type  TEXT    NOT NULL,
    symbol    TEXT,
    message   TEXT    NOT NULL,
    meta      TEXT    DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(log_type);
"""


class LogDB:
    """SQLite 로그 저장소 (동기 버전)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or DEFAULT_LOG_DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """DB 초기화 및 테이블 생성."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self._path)) as conn:
            conn.executescript(_CREATE_TABLE_SQL)
        logger.debug("로그 DB 초기화: %s", self._path)

    def write(
        self,
        log_type: str,
        message: str,
        symbol: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """로그를 기록하고 생성된 ID를 반환한다.

        Args:
            log_type: 로그 종류 (LOG_TYPE_* 상수 사용 권장)
            message: 로그 메시지
            symbol: 관련 종목 코드 (없으면 None)
            meta: 추가 메타데이터 (JSON 직렬화 가능한 딕셔너리)

        Returns:
            생성된 로그 레코드 ID
        """
        ts = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(meta or {}, ensure_ascii=False)

        with sqlite3.connect(str(self._path)) as conn:
            cursor = conn.execute(
                "INSERT INTO logs (ts, log_type, symbol, message, meta) VALUES (?, ?, ?, ?, ?)",
                (ts, log_type, symbol, message, meta_json),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def query(
        self,
        log_type: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """로그를 조회한다.

        Args:
            log_type: 필터할 로그 종류 (None이면 전체)
            symbol: 필터할 종목 코드 (None이면 전체)
            limit: 최대 조회 수
            offset: 건너뛸 수

        Returns:
            (로그 목록, 전체 건수) 튜플
        """
        conditions: list[str] = []
        params: list[Any] = []

        if log_type:
            conditions.append("log_type = ?")
            params.append(log_type)
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with sqlite3.connect(str(self._path)) as conn:
            conn.row_factory = sqlite3.Row

            # 전체 건수
            count_row = conn.execute(
                f"SELECT COUNT(*) FROM logs {where}", params
            ).fetchone()
            total = count_row[0] if count_row else 0

            # 데이터 조회
            rows = conn.execute(
                f"SELECT * FROM logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        items = [
            {
                "id": row["id"],
                "ts": row["ts"],
                "log_type": row["log_type"],
                "symbol": row["symbol"],
                "message": row["message"],
                "meta": json.loads(row["meta"] or "{}"),
            }
            for row in rows
        ]
        return items, total

    def today_realized_pnl(self) -> "Decimal":
        """당일 FILL 로그의 실현손익(realized_pnl)을 합산한다."""
        from decimal import Decimal

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(str(self._path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT meta FROM logs WHERE log_type = ? AND ts >= ?",
                (LOG_TYPE_FILL, today),
            ).fetchall()

        total = Decimal("0")
        for row in rows:
            meta = json.loads(row["meta"] or "{}")
            pnl = meta.get("realized_pnl")
            if pnl:
                total += Decimal(str(pnl))
        return total


# 전역 싱글턴
_log_db_instance: LogDB | None = None


def get_log_db() -> LogDB:
    """전역 로그 DB 인스턴스를 반환한다."""
    global _log_db_instance
    if _log_db_instance is None:
        _log_db_instance = LogDB()
    return _log_db_instance
