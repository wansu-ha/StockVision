"""AI 크레딧 관리 서비스."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.models.ai_usage import AIUsage
from cloud_server.models.ai_api_key import AIApiKey
from cloud_server.core.encryption import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


class CreditService:
    """토큰 기반 일일 크레딧 관리."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_daily(self, user_id: str) -> AIUsage:
        """오늘자 사용량 레코드 조회/생성."""
        today = date.today()
        usage = self.db.query(AIUsage).filter(
            AIUsage.user_id == user_id,
            AIUsage.date == today,
        ).first()
        if usage is None:
            usage = AIUsage(
                user_id=user_id,
                date=today,
                tokens_used=0,
                tokens_limit=settings.AI_DAILY_TOKEN_LIMIT,
            )
            self.db.add(usage)
            self.db.flush()
        return usage

    def deduct(self, user_id: str, tokens: int) -> None:
        """토큰 차감. 한도 초과 시 ValueError."""
        if self.is_byo_user(user_id):
            return  # BYO 사용자는 크레딧 무제한
        usage = self.get_or_create_daily(user_id)
        if usage.tokens_used + tokens > usage.tokens_limit:
            raise ValueError("일일 크레딧 소진")
        usage.tokens_used += tokens
        usage.updated_at = datetime.now(timezone.utc)

    def get_balance(self, user_id: str) -> dict:
        """크레딧 잔량 정보."""
        usage = self.get_or_create_daily(user_id)
        remaining = max(0, usage.tokens_limit - usage.tokens_used)
        pct = round(remaining / usage.tokens_limit * 100) if usage.tokens_limit > 0 else 0
        avg_per_turn = 2000  # 예상 평균 토큰
        estimate = remaining // avg_per_turn if avg_per_turn > 0 else 0
        return {
            "tokens_used": usage.tokens_used,
            "tokens_limit": usage.tokens_limit,
            "remaining_percent": pct,
            "estimate_turns": estimate,
            "resets_at": f"{date.today().isoformat()}T15:00:00+09:00",  # 자정 KST ≈ 15:00 UTC
            "has_byo_key": self.is_byo_user(user_id),
        }

    def is_byo_user(self, user_id: str) -> bool:
        """BYO API Key 등록 여부."""
        return self.db.query(AIApiKey).filter(AIApiKey.user_id == user_id).first() is not None

    def get_byo_key(self, user_id: str) -> str | None:
        """BYO API Key 복호화 반환. 없으면 None."""
        row = self.db.query(AIApiKey).filter(AIApiKey.user_id == user_id).first()
        if row is None:
            return None
        return decrypt_value(row.encrypted_key)

    def register_byo_key(self, user_id: str, api_key: str) -> None:
        """BYO API Key 등록/갱신."""
        row = self.db.query(AIApiKey).filter(AIApiKey.user_id == user_id).first()
        encrypted = encrypt_value(api_key)
        if row is None:
            self.db.add(AIApiKey(user_id=user_id, encrypted_key=encrypted))
        else:
            row.encrypted_key = encrypted
        self.db.flush()

    def delete_byo_key(self, user_id: str) -> bool:
        """BYO API Key 삭제. 삭제 성공 시 True."""
        row = self.db.query(AIApiKey).filter(AIApiKey.user_id == user_id).first()
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        return True
