"""이메일 발송 서비스 — SendGrid HTTP API.

인증 메일, 비밀번호 재설정, 디바이스 등록 알림 발송.
"""
from __future__ import annotations

import logging

import httpx

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailService:
    """SendGrid 기반 이메일 발송."""

    def __init__(self, api_key: str = "", from_email: str = ""):
        self._api_key = api_key or settings.EMAIL_API_KEY
        self._from = from_email or settings.EMAIL_FROM

    async def send_verification(self, to: str, token: str) -> None:
        """이메일 인증 메일 발송."""
        verify_url = f"{settings.CLOUD_URL}/api/v1/auth/verify-email?token={token}"
        await self._send(
            to=to,
            subject="StockVision 이메일 인증",
            html=f"""
            <h2>이메일 인증</h2>
            <p>아래 링크를 클릭하여 이메일을 인증하세요:</p>
            <a href="{verify_url}">이메일 인증하기</a>
            <p>이 링크는 24시간 후 만료됩니다.</p>
            """,
        )

    async def send_password_reset(self, to: str, token: str) -> None:
        """비밀번호 재설정 메일 발송."""
        reset_url = f"{settings.CLOUD_URL}/reset-password?token={token}"
        await self._send(
            to=to,
            subject="StockVision 비밀번호 재설정",
            html=f"""
            <h2>비밀번호 재설정</h2>
            <p>아래 링크를 클릭하여 비밀번호를 재설정하세요:</p>
            <a href="{reset_url}">비밀번호 재설정</a>
            <p>이 링크는 10분 후 만료됩니다.</p>
            """,
        )

    async def send_device_alert(self, to: str, device_name: str) -> None:
        """새 디바이스 등록 알림."""
        await self._send(
            to=to,
            subject="StockVision 새 디바이스 등록",
            html=f"""
            <h2>새 디바이스 등록</h2>
            <p>새로운 디바이스 <strong>{device_name}</strong>이(가) 등록되었습니다.</p>
            <p>본인이 아니라면 즉시 디바이스를 해제하세요.</p>
            """,
        )

    async def _send(self, to: str, subject: str, html: str) -> None:
        """SendGrid HTTP API로 메일 발송."""
        if not self._api_key:
            logger.warning("EMAIL_API_KEY 미설정, 이메일 발송 건너뜀: to=%s, subject=%s", to, subject)
            return

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._from},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    SENDGRID_API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code >= 400:
                    logger.error("이메일 발송 실패: status=%d, body=%s", resp.status_code, resp.text)
                else:
                    logger.info("이메일 발송 완료: to=%s", to)
        except Exception as e:
            logger.error("이메일 발송 오류: %s", e)
