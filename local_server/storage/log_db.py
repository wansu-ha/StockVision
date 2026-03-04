"""
실행 로그 SQLite DB (logs.db)

- 자동매매 실행 이력 저장
- 체결 시 filled_price / filled_qty 업데이트
- 날짜 범위 / rule_id 필터 조회
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent / "logs.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id            INTEGER NOT NULL,
                rule_name          TEXT,
                symbol             TEXT NOT NULL,
                side               TEXT NOT NULL,
                quantity           INTEGER NOT NULL,
                order_no           TEXT,
                filled_price       REAL,
                filled_qty         INTEGER,
                status             TEXT NOT NULL,
                condition_snapshot TEXT,
                message            TEXT,
                created_at         TEXT NOT NULL
            )
        """)
        # 구버전 컬럼 마이그레이션 (stock_code → symbol)
        try:
            c.execute("ALTER TABLE execution_logs ADD COLUMN symbol TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE execution_logs ADD COLUMN order_no TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE execution_logs ADD COLUMN filled_price REAL")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE execution_logs ADD COLUMN filled_qty INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE execution_logs ADD COLUMN condition_snapshot TEXT")
        except sqlite3.OperationalError:
            pass


def log_execution(rule_id: int, rule_name: str, side: str,
                  stock_code: str, quantity: int, status: str,
                  message: str = "",
                  order_no: str = "",
                  condition_snapshot: str = "") -> None:
    with _conn() as c:
        c.execute(
            """INSERT INTO execution_logs
               (rule_id, rule_name, symbol, side, quantity, order_no,
                status, condition_snapshot, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rule_id, rule_name, stock_code, side, quantity, order_no or None,
             status, condition_snapshot or None, message,
             datetime.utcnow().isoformat()),
        )


def log_fill(order_no: str, filled_price: float, filled_qty: int) -> None:
    """체결 콜백에서 호출 — filled_price/filled_qty 업데이트"""
    with _conn() as c:
        c.execute(
            """UPDATE execution_logs
               SET filled_price = ?, filled_qty = ?, status = 'FILLED'
               WHERE order_no = ? AND status = 'SENT'""",
            (filled_price, filled_qty, order_no),
        )


def query_logs(rule_id: int | None = None,
               date_from: str | None = None,
               date_to: str | None = None,
               limit: int = 100,
               offset: int = 0) -> list[dict]:
    """실행 로그 조회 (최신순)"""
    conditions = []
    params: list = []

    if rule_id is not None:
        conditions.append("rule_id = ?")
        params.append(rule_id)
    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("created_at <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM execution_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def query_summary_today() -> dict:
    """오늘 실행 수 / 체결 수 / 오류 수"""
    today = datetime.utcnow().date().isoformat()
    with _conn() as c:
        total  = c.execute("SELECT COUNT(*) FROM execution_logs WHERE created_at >= ?", (today,)).fetchone()[0]
        filled = c.execute("SELECT COUNT(*) FROM execution_logs WHERE created_at >= ? AND status = 'FILLED'", (today,)).fetchone()[0]
        failed = c.execute("SELECT COUNT(*) FROM execution_logs WHERE created_at >= ? AND status IN ('FAILED','ERROR')", (today,)).fetchone()[0]
    return {"total": total, "filled": filled, "failed": failed}
