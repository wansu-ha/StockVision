"""
일일 이메일 요약 발송

- 16:00 KST 장 마감 후 스케줄러에서 호출
- 오늘 실행 건 > 0인 경우에만 발송
- 클라우드 백엔드의 이메일 API 사용 (SMTP 설정은 서버 측)
"""
import logging
import os
from datetime import datetime

import httpx
import pytz

_KST = pytz.timezone("Asia/Seoul")

logger = logging.getLogger(__name__)

_CLOUD_URL = os.environ.get("CLOUD_URL", "https://stockvision.app")


def send_daily_summary(jwt: str) -> None:
    """장 마감 후 일일 요약 이메일 발송"""
    from storage.log_db import query_summary_today, query_logs
    summary = query_summary_today()

    if summary["total"] == 0:
        logger.info("오늘 실행 없음 — 이메일 생략")
        return

    logs = query_logs(limit=20)
    today = datetime.now(_KST).date().isoformat()

    body_lines = [
        f"■ 오늘({today}) 자동매매 요약",
        f"  실행: {summary['total']}건 / 체결: {summary['filled']}건 / 오류: {summary['failed']}건",
        "",
        "■ 체결 내역",
    ]
    for log in logs:
        if log.get("status") == "FILLED":
            body_lines.append(
                f"  {log['rule_name']}  {log['side']}  {log['symbol']}  "
                f"{log['quantity']}주  @{log.get('filled_price', '-'):,.0f}원"
                if isinstance(log.get("filled_price"), (int, float))
                else f"  {log['rule_name']}  {log['side']}  {log['symbol']}  {log['quantity']}주"
            )

    try:
        resp = httpx.post(
            f"{_CLOUD_URL}/api/notify/email",
            json={
                "subject": f"[StockVision] 오늘 거래 요약 ({today})",
                "body":    "\n".join(body_lines),
            },
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("일일 이메일 요약 발송 완료")
    except Exception as e:
        logger.warning(f"이메일 발송 실패 (cloud API): {e}")
