"""sv_core.broker.models: 브로커 공통 데이터 모델"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "BUY"    # 매수
    SELL = "SELL"  # 매도


class OrderType(str, Enum):
    """주문 유형"""
    MARKET = "MARKET"  # 시장가
    LIMIT = "LIMIT"    # 지정가


class OrderStatus(str, Enum):
    """주문 상태"""
    NEW = "NEW"                      # 신규 (접수 전)
    SUBMITTED = "SUBMITTED"          # 접수됨
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 부분 체결
    FILLED = "FILLED"                # 완전 체결
    CANCELLED = "CANCELLED"          # 취소됨
    REJECTED = "REJECTED"            # 거부됨


class ErrorCategory(str, Enum):
    """에러 분류"""
    TRANSIENT = "TRANSIENT"      # 일시적 에러 (재시도 가능)
    PERMANENT = "PERMANENT"      # 영구 에러 (재시도 불가)
    RATE_LIMIT = "RATE_LIMIT"    # 속도 제한
    AUTH = "AUTH"                # 인증 에러
    UNKNOWN = "UNKNOWN"          # 미분류


@dataclass
class OrderResult:
    """주문 결과"""
    order_id: str               # 브로커 주문 ID
    client_order_id: str        # 클라이언트 주문 ID (멱등성 키)
    symbol: str                 # 종목 코드
    side: OrderSide             # 주문 방향
    order_type: OrderType       # 주문 유형
    qty: int                    # 주문 수량
    limit_price: Optional[Decimal]  # 지정가 (시장가면 None)
    status: OrderStatus         # 주문 상태
    filled_qty: int = 0         # 체결 수량
    filled_avg_price: Optional[Decimal] = None  # 평균 체결가
    submitted_at: Optional[datetime] = None     # 접수 시각
    raw: dict = field(default_factory=dict)     # 원본 응답


@dataclass
class BalanceResult:
    """잔고 조회 결과"""
    cash: Decimal               # 현금 잔고
    total_eval: Decimal         # 총 평가 금액 (현금 + 보유 주식 평가액)
    positions: list["Position"] = field(default_factory=list)  # 보유 포지션
    raw: dict = field(default_factory=dict)  # 원본 응답


@dataclass
class Position:
    """보유 포지션"""
    symbol: str                 # 종목 코드
    qty: int                    # 보유 수량
    avg_price: Decimal          # 평균 매수가
    current_price: Decimal      # 현재가
    eval_amount: Decimal        # 평가 금액
    unrealized_pnl: Decimal     # 미실현 손익
    unrealized_pnl_rate: Decimal  # 미실현 손익률 (%)


@dataclass
class QuoteEvent:
    """실시간 시세 이벤트"""
    symbol: str                 # 종목 코드
    price: Decimal              # 현재가
    volume: int                 # 거래량
    bid_price: Optional[Decimal] = None  # 매수호가
    ask_price: Optional[Decimal] = None  # 매도호가
    timestamp: Optional[datetime] = None  # 체결 시각
    raw: dict = field(default_factory=dict)  # 원본 메시지
