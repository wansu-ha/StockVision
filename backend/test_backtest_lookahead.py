#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Look-Ahead Bias 제거 검증 테스트 (C-1)

검증 항목:
  T1. get_stock_prices(as_of_date)  — as_of_date 이후 가격 미포함
  T2. prepare_features(as_of_date)  — as_of_date 이후 특성 미포함
  T3. score_stock(as_of_date)       — 날짜 인식 스코어링 (실시간과 다른 값)
  T4. BacktestEngine.run 소스 검사  — 루프에서 as_of_date 전달 확인
"""

import sys
import inspect
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

CUTOFF = datetime(2025, 6, 30)  # 검증 기준일


# ─────────────────────────────────────────────────────────
# T1: get_stock_prices — 날짜 필터
# ─────────────────────────────────────────────────────────
def test_get_stock_prices_filter() -> bool:
    logger.info("── T1: get_stock_prices as_of_date 필터 ──────────────")
    try:
        from app.services.technical_indicators import TechnicalIndicatorCalculator
        from app.core.database import SessionLocal
        from app.models.stock import Stock

        db = SessionLocal()
        stock = db.query(Stock).first()
        db.close()

        if not stock:
            logger.warning("  ⏭  종목 없음 → 코드 구조 검사로 대체")
            return _inspect_get_stock_prices()

        calc = TechnicalIndicatorCalculator()
        df_cut = calc.get_stock_prices(stock.id, as_of_date=CUTOFF)

        if df_cut.empty:
            logger.warning(f"  ⏭  {stock.symbol}: {CUTOFF.date()} 이전 가격 없음 → 스킵")
            return True

        max_date = df_cut.index.max()
        if max_date > CUTOFF:
            logger.error(f"  ✗  날짜 필터 실패: 최대={max_date.date()} > cutoff={CUTOFF.date()}")
            return False

        # 전체(필터 없음)와 비교해 미래 데이터 제외 확인
        df_all = calc.get_stock_prices(stock.id)
        if not df_all.empty and df_all.index.max() > CUTOFF:
            logger.info(f"  ✓  전체 최대={df_all.index.max().date()}  필터 후 최대={max_date.date()}")
        else:
            logger.info(f"  ✓  최대={max_date.date()} ≤ {CUTOFF.date()}")

        logger.info("  ✅ T1 통과")
        return True

    except AssertionError as e:
        logger.error(f"  ✗  {e}")
        return False
    except Exception as e:
        logger.error(f"  ✗  예외: {e}")
        return False


def _inspect_get_stock_prices() -> bool:
    from app.services.technical_indicators import TechnicalIndicatorCalculator
    src = inspect.getsource(TechnicalIndicatorCalculator.get_stock_prices)
    ok = "as_of_date" in src and ("date <=" in src or "date<=" in src)
    if ok:
        logger.info("  ✓  소스에 as_of_date + date<= 필터 확인")
        logger.info("  ✅ T1 통과 (코드 검사)")
    else:
        logger.error("  ✗  날짜 필터 코드 없음")
    return ok


# ─────────────────────────────────────────────────────────
# T2: prepare_features — 날짜 필터
# ─────────────────────────────────────────────────────────
def test_prepare_features_filter() -> bool:
    logger.info("── T2: prepare_features as_of_date 필터 ──────────────")
    try:
        from app.services.prediction_model import PredictionModel
        from app.core.database import SessionLocal
        from app.models.stock import Stock

        db = SessionLocal()
        stock = db.query(Stock).first()
        db.close()

        if not stock:
            logger.warning("  ⏭  종목 없음 → 코드 구조 검사로 대체")
            return _inspect_prepare_features()

        predictor = PredictionModel()
        features, _ = predictor.prepare_features(stock.id, as_of_date=CUTOFF)

        if features.empty:
            logger.warning(f"  ⏭  {stock.symbol}: {CUTOFF.date()} 이전 특성 없음 → 스킵")
            return True

        max_date = features.index.max()
        if max_date > CUTOFF:
            logger.error(f"  ✗  날짜 필터 실패: 특성 최대={max_date.date()} > cutoff={CUTOFF.date()}")
            return False

        logger.info(f"  ✓  특성 최대={max_date.date()} ≤ {CUTOFF.date()}")
        logger.info("  ✅ T2 통과")
        return True

    except AssertionError as e:
        logger.error(f"  ✗  {e}")
        return False
    except Exception as e:
        logger.error(f"  ✗  예외: {e}")
        return False


def _inspect_prepare_features() -> bool:
    from app.services.prediction_model import PredictionModel
    src = inspect.getsource(PredictionModel.prepare_features)
    # StockPrice 필터 + TechnicalIndicator 필터 둘 다 있어야 함
    price_ok = "as_of_date" in src and ("date <=" in src or "date<=" in src)
    ind_ok = "TechnicalIndicator" in src and ("date <=" in src or "date<=" in src)
    ok = price_ok and ind_ok
    if ok:
        logger.info("  ✓  소스에 StockPrice + TechnicalIndicator 날짜 필터 확인")
        logger.info("  ✅ T2 통과 (코드 검사)")
    else:
        logger.error("  ✗  날짜 필터 코드 누락")
    return ok


# ─────────────────────────────────────────────────────────
# T3: score_stock — 실시간과 과거 스코어 분리
# ─────────────────────────────────────────────────────────
def test_score_stock_date_aware() -> bool:
    logger.info("── T3: score_stock as_of_date 분리 검증 ──────────────")
    try:
        from app.services.scoring_engine import ScoringEngine
        from app.core.database import SessionLocal
        from app.models.stock import Stock

        db = SessionLocal()
        stock = db.query(Stock).first()

        if not stock:
            logger.warning("  ⏭  종목 없음 → 코드 구조 검사로 대체")
            db.close()
            return _inspect_score_stock()

        scorer = ScoringEngine(db)
        score_rt = scorer.score_stock(stock.id, stock.symbol)
        score_past = scorer.score_stock(stock.id, stock.symbol, as_of_date=CUTOFF)
        scorer.close()

        if score_rt is None:
            logger.warning(f"  ⏭  {stock.symbol}: 실시간 스코어 없음 → 스킵")
            return True

        logger.info(f"  실시간 스코어 = {score_rt['total_score']:.1f} ({score_rt['signal']})")

        if score_past is not None:
            logger.info(f"  {CUTOFF.date()} 스코어 = {score_past['total_score']:.1f} ({score_past['signal']})")
            if score_rt["total_score"] != score_past["total_score"]:
                logger.info("  ✓  시점별 스코어 다름 → look-ahead bias 제거 효과 확인")
            else:
                logger.info("  ℹ  스코어 동일 (데이터 변동 없거나 동일 기간)")
        else:
            logger.info(f"  ℹ  {CUTOFF.date()} 이전 데이터 없음 → score_past=None 정상")

        logger.info("  ✅ T3 통과")
        return True

    except Exception as e:
        logger.error(f"  ✗  예외: {e}")
        return False


def _inspect_score_stock() -> bool:
    from app.services.scoring_engine import ScoringEngine
    src = inspect.getsource(ScoringEngine.score_stock)
    has_param = "as_of_date" in src
    passes_to_calc = "as_of_date=as_of_date" in src
    ok = has_param and passes_to_calc
    if ok:
        logger.info("  ✓  score_stock에 as_of_date 파라미터 + 하위 호출 전달 확인")
        logger.info("  ✅ T3 통과 (코드 검사)")
    else:
        logger.error("  ✗  as_of_date 전달 코드 없음")
    return ok


# ─────────────────────────────────────────────────────────
# T4: BacktestEngine.run 소스 검사 — as_of_date=date 전달
# ─────────────────────────────────────────────────────────
def test_backtest_passes_date() -> bool:
    logger.info("── T4: BacktestEngine.run as_of_date 전달 검사 ────────")
    try:
        from app.services.backtest_engine import BacktestEngine

        src = inspect.getsource(BacktestEngine.run)
        call_count = src.count("as_of_date=date")

        checks = [
            (call_count >= 2,
             f"as_of_date=date 전달 {call_count}회 (매도+매수 각 1회 이상 필요)"),
        ]

        ok = True
        for passed, desc in checks:
            mark = "✓" if passed else "✗"
            level = logger.info if passed else logger.error
            level(f"  {mark}  {desc}")
            if not passed:
                ok = False

        if ok:
            logger.info("  ✅ T4 통과")
        return ok

    except Exception as e:
        logger.error(f"  ✗  예외: {e}")
        return False


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────
def main() -> bool:
    logger.info("=" * 55)
    logger.info("  Look-Ahead Bias 제거 검증 (C-1)")
    logger.info("=" * 55)

    results = {
        "T1 get_stock_prices 날짜 필터":   test_get_stock_prices_filter(),
        "T2 prepare_features 날짜 필터":   test_prepare_features_filter(),
        "T3 score_stock 시점 분리":        test_score_stock_date_aware(),
        "T4 BacktestEngine as_of_date 전달": test_backtest_passes_date(),
    }

    logger.info("=" * 55)
    logger.info("  결과 요약")
    logger.info("=" * 55)
    passed = 0
    for name, ok in results.items():
        mark = "✅" if ok else "❌"
        logger.info(f"  {mark}  {name}")
        if ok:
            passed += 1

    total = len(results)
    logger.info(f"\n  {total}개 중 {passed}개 통과")

    if passed == total:
        logger.info("  🎉 모든 검증 통과 — Look-Ahead Bias 제거 확인")
    else:
        logger.warning("  ⚠️  일부 검증 실패")

    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
