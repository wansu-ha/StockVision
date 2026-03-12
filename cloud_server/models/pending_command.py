"""오프라인 명령 큐 모델.

로컬 서버 오프라인 시 원격 디바이스 명령을 저장하고,
로컬 재연결 시 flush한다.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.types import JSON

from cloud_server.core.database import Base


class PendingCommand(Base):
    __tablename__ = "pending_commands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    command_type = Column(String(50))  # 'kill', 'arm', ...
    payload = Column(JSON)
    status = Column(String(20), default="pending")  # pending / executed / expired
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
