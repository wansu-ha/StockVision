"""이메일 발송 유틸리티 — Provider 패턴.

EMAIL_PROVIDER 환경변수로 백엔드 선택:
  resend   → Resend HTTP API (RESEND_API_KEY 필요)
  sendgrid → SendGrid HTTP API (EMAIL_API_KEY 필요)
  smtp     → Gmail 등 SMTP 서버 (SMTP_USER, SMTP_PASSWORD 필요) — 클라우드 호스팅에서 차단될 수 있음
  (빈값)   → 로그 출력만 (개발 환경)
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Protocol

import httpx

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)


# ── Provider 인터페이스 ──────────────────────────────────────
class EmailProvider(Protocol):
    def send(self, to: str, subject: str, html: str) -> None: ...


# ── SMTP (Gmail 등) ─────────────────────────────────────────
class SmtpProvider:
    def send(self, to: str, subject: str, html: str) -> None:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP_USER/SMTP_PASSWORD 미설정, 이메일 건너뜀: to=%s", to)
            return

        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("이메일 발송 완료 (SMTP): to=%s", to)
        except Exception as e:
            logger.error("이메일 발송 실패 (SMTP): %s", e)


# ── SendGrid HTTP API ───────────────────────────────────────
class SendGridProvider:
    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

    def send(self, to: str, subject: str, html: str) -> None:
        if not settings.EMAIL_API_KEY:
            logger.warning("EMAIL_API_KEY 미설정, 이메일 건너뜀: to=%s", to)
            return

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": settings.EMAIL_FROM},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        }

        try:
            resp = httpx.post(
                self.SENDGRID_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.EMAIL_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code >= 400:
                logger.error("이메일 발송 실패 (SendGrid): status=%d, body=%s", resp.status_code, resp.text)
            else:
                logger.info("이메일 발송 완료 (SendGrid): to=%s", to)
        except Exception as e:
            logger.error("이메일 발송 오류 (SendGrid): %s", e)


# ── Resend HTTP API ──────────────────────────────────────────
class ResendProvider:
    RESEND_API_URL = "https://api.resend.com/emails"

    def send(self, to: str, subject: str, html: str) -> None:
        api_key = os.environ.get("RESEND_API_KEY", "")
        if not api_key:
            logger.warning("RESEND_API_KEY 미설정, 이메일 건너뜀: to=%s", to)
            return

        payload = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        try:
            resp = httpx.post(
                self.RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code >= 400:
                logger.error("이메일 발송 실패 (Resend): status=%d, body=%s", resp.status_code, resp.text)
            else:
                logger.info("이메일 발송 완료 (Resend): to=%s", to)
        except Exception as e:
            logger.error("이메일 발송 오류 (Resend): %s", e)


# ── 로그 전용 (개발) ────────────────────────────────────────
class LogProvider:
    def send(self, to: str, subject: str, html: str) -> None:
        logger.info("[이메일 미발송 — provider 미설정] to=%s subject=%s", to, subject)


# ── Provider 레지스트리 ──────────────────────────────────────
_PROVIDERS: dict[str, type[EmailProvider]] = {
    "resend": ResendProvider,
    "smtp": SmtpProvider,
    "sendgrid": SendGridProvider,
}


def _get_provider() -> EmailProvider:
    provider_name = settings.EMAIL_PROVIDER.lower().strip()
    cls = _PROVIDERS.get(provider_name)
    if cls:
        return cls()
    return LogProvider()


_provider = _get_provider()


# ── 공개 API (auth 라우터에서 호출) ──────────────────────────
def send_verification_email(to: str, token: str) -> None:
    """이메일 인증 링크 발송."""
    link = f"{settings.CLOUD_URL}/api/v1/auth/verify-email?token={token}"
    _provider.send(
        to=to,
        subject="[StockVision] 이메일 인증",
        html=(
            f"<p>아래 링크를 클릭하여 이메일을 인증하세요 (24시간 유효):</p>"
            f'<p><a href="{link}">{link}</a></p>'
        ),
    )


def send_password_reset_email(to: str, token: str) -> None:
    """비밀번호 재설정 링크 발송."""
    link = f"{settings.CLOUD_URL}/reset-password?token={token}"
    _provider.send(
        to=to,
        subject="[StockVision] 비밀번호 재설정",
        html=(
            f"<p>아래 링크를 클릭하여 비밀번호를 재설정하세요 (10분 유효):</p>"
            f'<p><a href="{link}">{link}</a></p>'
        ),
    )
