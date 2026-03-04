import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
_HOST    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
_PORT    = int(os.environ.get("SMTP_PORT", "587"))
_USER    = os.environ.get("SMTP_USER", "")
_PASS    = os.environ.get("SMTP_PASSWORD", "")
_FROM    = os.environ.get("SMTP_FROM", _USER)


def send_email(to: str, subject: str, body: str) -> None:
    """이메일 발송. SMTP_ENABLED=false(기본)이면 로그로만 출력"""
    if not _ENABLED:
        logger.info(f"[SMTP 비활성화] to={to} subject={subject}\n{body}")
        return

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = _FROM
    msg["To"]      = to

    with smtplib.SMTP(_HOST, _PORT) as server:
        server.starttls()
        server.login(_USER, _PASS)
        server.send_message(msg)


def send_verification_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/api/auth/verify-email?token={token}"
    send_email(
        to=to,
        subject="[StockVision] 이메일 인증",
        body=f"<p>아래 링크를 클릭하여 이메일을 인증하세요 (24시간 유효):</p><p><a href='{link}'>{link}</a></p>",
    )


def send_password_reset_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/reset-password?token={token}"
    send_email(
        to=to,
        subject="[StockVision] 비밀번호 재설정",
        body=f"<p>아래 링크를 클릭하여 비밀번호를 재설정하세요 (10분 유효):</p><p><a href='{link}'>{link}</a></p>",
    )
