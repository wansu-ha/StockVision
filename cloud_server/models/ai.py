"""AI 분석 이력 모델"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from cloud_server.core.database import Base


class AIAnalysisLog(Base):
    """AI 분석 호출 이력"""
    __tablename__ = "ai_analysis_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    type = Column(String(20), nullable=False)       # sentiment|summary|risk|technical
    source = Column(String(20), nullable=False)      # claude|stub
    score = Column(Float, nullable=True)
    text = Column(Text, nullable=True)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    model = Column(String(50), default="")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
