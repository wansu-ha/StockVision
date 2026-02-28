"""
가상 거래 엔진

매수/매도 주문 처리, 포지션 관리, 손익 계산.
수수료: 매수 0.015%, 매도 0.015% + 세금 0.23%
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.virtual_trading import VirtualAccount, VirtualPosition, VirtualTrade

logger = logging.getLogger(__name__)

# 수수료/세금 상수
BUY_COMMISSION_RATE = 0.00015   # 매수 수수료 0.015%
SELL_COMMISSION_RATE = 0.00015  # 매도 수수료 0.015%
SELL_TAX_RATE = 0.0023          # 매도 세금 0.23%


class TradingEngine:
    """가상 거래 엔진"""

    def __init__(self, db: Session):
        self.db = db

    # ── 계좌 관리 ──

    def create_account(self, name: str, initial_balance: float = 10_000_000.0) -> VirtualAccount:
        """가상 계좌 생성"""
        account = VirtualAccount(
            name=name,
            initial_balance=initial_balance,
            current_balance=initial_balance,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        logger.info(f"계좌 생성: {account.id} ({name}, {initial_balance:,.0f}원)")
        return account

    def get_account(self, account_id: int) -> Optional[VirtualAccount]:
        """계좌 조회"""
        return self.db.query(VirtualAccount).filter(VirtualAccount.id == account_id).first()

    def get_accounts(self) -> list[VirtualAccount]:
        """전체 계좌 목록"""
        return self.db.query(VirtualAccount).all()

    def get_account_summary(self, account_id: int) -> Optional[dict]:
        """계좌 요약 (잔고 + 포지션 가치 + 수익률)"""
        account = self.get_account(account_id)
        if not account:
            return None

        positions = self.get_positions(account_id)
        total_position_value = sum(
            (p.current_price or p.avg_price) * p.quantity for p in positions
        )
        total_assets = account.current_balance + total_position_value
        total_return_rate = ((total_assets - account.initial_balance) / account.initial_balance) * 100

        win_rate = 0.0
        if account.total_trades > 0:
            win_rate = (account.win_trades / account.total_trades) * 100

        return {
            "account_id": account.id,
            "name": account.name,
            "initial_balance": account.initial_balance,
            "current_balance": account.current_balance,
            "total_position_value": total_position_value,
            "total_assets": total_assets,
            "total_return_rate": round(total_return_rate, 2),
            "total_profit_loss": account.total_profit_loss,
            "total_trades": account.total_trades,
            "win_trades": account.win_trades,
            "win_rate": round(win_rate, 2),
            "positions": len(positions),
        }

    # ── 주문 처리 ──

    def buy(
        self,
        account_id: int,
        stock_id: int,
        symbol: str,
        quantity: int,
        price: float,
    ) -> dict:
        """매수 주문

        Returns:
            {"success": bool, "message": str, "trade": VirtualTrade | None}
        """
        account = self.get_account(account_id)
        if not account:
            return {"success": False, "message": "계좌를 찾을 수 없습니다", "trade": None}

        total_amount = price * quantity
        commission = total_amount * BUY_COMMISSION_RATE
        required = total_amount + commission

        if account.current_balance < required:
            return {
                "success": False,
                "message": f"잔고 부족 (필요: {required:,.0f}원, 잔고: {account.current_balance:,.0f}원)",
                "trade": None,
            }

        # 잔고 차감
        account.current_balance -= required
        account.updated_at = datetime.utcnow()

        # 포지션 생성/업데이트
        position = (
            self.db.query(VirtualPosition)
            .filter(VirtualPosition.account_id == account_id, VirtualPosition.stock_id == stock_id)
            .first()
        )

        if position:
            # 기존 포지션 — 평균 매입가 재계산
            total_cost = position.avg_price * position.quantity + total_amount
            position.quantity += quantity
            position.avg_price = total_cost / position.quantity
            position.current_price = price
            position.unrealized_pnl = (price - position.avg_price) * position.quantity
            position.updated_at = datetime.utcnow()
        else:
            position = VirtualPosition(
                account_id=account_id,
                stock_id=stock_id,
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                unrealized_pnl=0.0,
            )
            self.db.add(position)

        # 거래 기록
        trade = VirtualTrade(
            account_id=account_id,
            stock_id=stock_id,
            symbol=symbol,
            trade_type="BUY",
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            commission=commission,
            tax=0.0,
            realized_pnl=None,
            timestamp=datetime.utcnow(),
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        logger.info(f"매수 완료: {symbol} {quantity}주 × {price:,.0f}원 (수수료 {commission:,.0f}원)")
        return {"success": True, "message": "매수 완료", "trade": trade}

    def sell(
        self,
        account_id: int,
        stock_id: int,
        symbol: str,
        quantity: int,
        price: float,
    ) -> dict:
        """매도 주문

        Returns:
            {"success": bool, "message": str, "trade": VirtualTrade | None}
        """
        account = self.get_account(account_id)
        if not account:
            return {"success": False, "message": "계좌를 찾을 수 없습니다", "trade": None}

        position = (
            self.db.query(VirtualPosition)
            .filter(VirtualPosition.account_id == account_id, VirtualPosition.stock_id == stock_id)
            .first()
        )

        if not position or position.quantity < quantity:
            available = position.quantity if position else 0
            return {
                "success": False,
                "message": f"보유 수량 부족 (보유: {available}주, 매도: {quantity}주)",
                "trade": None,
            }

        total_amount = price * quantity
        commission = total_amount * SELL_COMMISSION_RATE
        tax = total_amount * SELL_TAX_RATE
        net_amount = total_amount - commission - tax

        # 실현 손익 계산
        buy_cost = position.avg_price * quantity
        realized_pnl = net_amount - buy_cost

        # 잔고 증가
        account.current_balance += net_amount
        account.total_profit_loss += realized_pnl
        account.total_trades += 1
        if realized_pnl > 0:
            account.win_trades += 1
        account.updated_at = datetime.utcnow()

        # 포지션 감소/삭제
        position.quantity -= quantity
        if position.quantity == 0:
            self.db.delete(position)
        else:
            position.current_price = price
            position.unrealized_pnl = (price - position.avg_price) * position.quantity
            position.updated_at = datetime.utcnow()

        # 거래 기록
        trade = VirtualTrade(
            account_id=account_id,
            stock_id=stock_id,
            symbol=symbol,
            trade_type="SELL",
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            commission=commission,
            tax=tax,
            realized_pnl=realized_pnl,
            timestamp=datetime.utcnow(),
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        logger.info(
            f"매도 완료: {symbol} {quantity}주 × {price:,.0f}원 "
            f"(수수료 {commission:,.0f}원, 세금 {tax:,.0f}원, 손익 {realized_pnl:,.0f}원)"
        )
        return {"success": True, "message": "매도 완료", "trade": trade}

    # ── 포지션/거래 내역 ──

    def get_positions(self, account_id: int) -> list[VirtualPosition]:
        """보유 포지션 목록"""
        return (
            self.db.query(VirtualPosition)
            .filter(VirtualPosition.account_id == account_id)
            .all()
        )

    def update_position_prices(self, account_id: int, prices: dict[int, float]):
        """포지션 현재가 일괄 업데이트

        Args:
            prices: {stock_id: current_price}
        """
        positions = self.get_positions(account_id)
        for pos in positions:
            if pos.stock_id in prices:
                pos.current_price = prices[pos.stock_id]
                pos.unrealized_pnl = (pos.current_price - pos.avg_price) * pos.quantity
                pos.updated_at = datetime.utcnow()
        self.db.commit()

    def get_trades(self, account_id: int, limit: int = 50) -> list[VirtualTrade]:
        """거래 내역 조회"""
        return (
            self.db.query(VirtualTrade)
            .filter(VirtualTrade.account_id == account_id)
            .order_by(VirtualTrade.timestamp.desc())
            .limit(limit)
            .all()
        )
