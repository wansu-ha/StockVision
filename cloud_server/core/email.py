"""
이메일 발송 유틸리티

SMTP_ENABLED=true 환경변수 없으면 로그로만 출력 (개발 환경)
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"


def send_email(to: str, subject: str, body: str) -> None:
    """이메일 발송. SMTP_ENABLED=false(기본)이면 로그로만 출력"""
    if not _ENABLED:
        logger.info(f"[SMTP 비활성화] to={to} subject={subject}\n{body}")
        return

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def send_verification_email(to: str, token: str) -> None:
    """이메일 인증 링크 발송"""
    link = f"{settings.CLOUD_URL}/api/v1/auth/verify-email?token={token}"
    send_email(
        to=to,
        subject="[StockVision] 이메일 인증",
        body=(
            f"<p>아래 링크를 클릭하여 이메일을 인증하세요 (24시간 유효):</p>"
            f"<p><a href='{link}'>{link}</a></p>"
        ),
    )


def send_password_reset_email(to: str, token: str) -> None:
    """비밀번호 재설정 링크 발송"""
    link = f"{settings.CLOUD_URL}/reset-password?token={token}"
    send_email(
        to=to,
        subject="[StockVision] 비밀번호 재설정",
        body=(
            f"<p>아래 링크를 클릭하여 비밀번호를 재설정하세요 (10분 유효):</p>"
            f"<p><a href='{link}'>{link}</a></p>"
        ),
    )
