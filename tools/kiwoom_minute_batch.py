"""키움 REST API 과거 분봉 배치 수집 스크립트.

키움 모의서버 또는 실서버에서 주요 종목의 과거 1분봉 데이터를 수집하여
JSON 파일로 저장한다. 이후 import_minute_bars.py로 cloud DB에 임포트.

사용법:
    # 모의서버 (기본)
    python -m tools.kiwoom_minute_batch --symbols 005930,000660 --output data/minute_bars

    # 실서버
    python -m tools.kiwoom_minute_batch --real --symbols 005930 --output data/minute_bars

    # 단일 종목 API 테스트 (응답 구조 확인)
    python -m tools.kiwoom_minute_batch --discover --symbols 005930

환경변수:
    KIWOOM_APP_KEY: 키움 앱 키
    KIWOOM_SECRET_KEY: 키움 시크릿 키
    (또는 keyring stockvision:test@stockvision.dev 에서 자동 로드)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import httpx

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from local_server.broker.kiwoom.auth import KiwoomAuth

logger = logging.getLogger(__name__)

# 키움 분봉 차트 — 모의서버 검증 완료 (2026-03-26)
API_ID_MINUTE_CHART = "ka10080"
CHART_ENDPOINT = "/api/dostk/chart"

# rate limit: 429 에러 확인됨. 1초 간격 안전.
RATE_LIMIT_INTERVAL = 1.0

# 주요 종목
DEFAULT_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "005380",  # 현대차
    "051910",  # LG화학
    "247540",  # 에코프로비엠
    "373220",  # LG에너지솔루션
    "035720",  # 카카오
    "006400",  # 삼성SDI
    "068270",  # 셀트리온
]


async def fetch_minute_bars(
    auth: KiwoomAuth,
    symbol: str,
    tick_unit: int = 1,
    max_pages: int = 500,
) -> list[dict]:
    """키움 REST API로 종목의 과거 분봉을 순차 조회.

    키움 API는 최신→과거 순으로 데이터를 반환하며,
    cont-yn / next-key로 페이징한다.

    Args:
        auth: 키움 인증 객체
        symbol: 종목코드 (예: "005930")
        tick_unit: 분 단위 (1, 3, 5, 10, 15, 30, 60)
        max_pages: 최대 페이지 수 (안전 장치)

    Returns:
        OHLCV 딕셔너리 리스트 (오래된 순)
    """
    all_bars: list[dict] = []
    next_key = ""
    page = 0

    while page < max_pages:
        headers = await auth.build_headers(API_ID_MINUTE_CHART)
        body: dict = {
            "stk_cd": symbol,
            "tic_scope": str(tick_unit),
            "upd_stkpc_tp": "1",  # 수정주가 적용
        }
        if next_key:
            headers["next-key"] = next_key

        url = f"{auth.base_url}{CHART_ENDPOINT}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP 에러 [%s] page=%d: %s", symbol, page, e)
            break
        except Exception as e:
            logger.error("요청 실패 [%s] page=%d: %s", symbol, page, e)
            break

        data = resp.json()

        if data.get("return_code") != 0:
            logger.error("API 에러 [%s]: %s", symbol, data.get("return_msg"))
            break

        # 차트 데이터 파싱 — 키워 필드명은 모의서버 응답으로 확인 필요
        # 일반적: output 또는 output1 배열 안에 개별 봉 데이터
        bars = _extract_bars(data)
        if not bars:
            logger.info("[%s] 더 이상 데이터 없음 (page=%d, total=%d)", symbol, page, len(all_bars))
            break

        all_bars.extend(bars)
        page += 1

        # 페이징 여부 확인
        cont_yn = resp.headers.get("cont-yn", data.get("cont_yn", "N"))
        next_key = resp.headers.get("next-key", data.get("next_key", ""))

        if cont_yn != "Y" or not next_key:
            logger.info("[%s] 수집 완료: %d건 (%d pages)", symbol, len(all_bars), page)
            break

        # rate limit
        await asyncio.sleep(RATE_LIMIT_INTERVAL)

        if page % 10 == 0:
            logger.info("[%s] 수집 중: %d건 (%d pages)", symbol, len(all_bars), page)

    # 동일 timestamp 중복 집계 (모의서버: 같은 분에 여러 체결건 반환)
    all_bars = _deduplicate_bars(all_bars)

    # 오래된 순 정렬
    all_bars.sort(key=lambda b: b.get("timestamp", ""))
    return all_bars


def _deduplicate_bars(bars: list[dict]) -> list[dict]:
    """동일 timestamp 봉을 OHLCV로 집계."""
    agg: dict[str, dict] = {}
    for b in bars:
        ts = b["timestamp"]
        if ts not in agg:
            agg[ts] = {**b}
        else:
            a = agg[ts]
            a["high"] = max(a["high"], b["high"])
            a["low"] = min(a["low"], b["low"])
            a["close"] = b["close"]
            a["volume"] += b["volume"]
    return list(agg.values())


def _extract_bars(data: dict) -> list[dict]:
    """API 응답에서 분봉 데이터를 추출.

    검증된 응답 구조 (2026-03-26 모의서버):
        data["stk_min_pole_chart_qry"]: list[dict]  (900건/페이지)
        각 항목: cur_prc, open_pric, high_pric, low_pric, trde_qty, cntr_tm
        가격에 부호 접두사: "+189900", "-189000" → abs(int()) 필요
    """
    bars_raw = data.get("stk_min_pole_chart_qry", [])

    # fallback: 다른 키 이름일 수 있음
    if not bars_raw:
        for key in data:
            if isinstance(data[key], list) and len(data[key]) > 0:
                first = data[key][0]
                if isinstance(first, dict) and "cntr_tm" in first:
                    bars_raw = data[key]
                    break

    result = []
    for item in bars_raw:
        ts = item.get("cntr_tm", "")
        close = abs(int(item.get("cur_prc", 0) or 0))
        if not ts or close == 0:
            continue

        result.append({
            "timestamp": ts,                                    # "20260325151900"
            "open": abs(int(item.get("open_pric", 0) or 0)),   # "+189800"
            "high": abs(int(item.get("high_pric", 0) or 0)),   # "+189900"
            "low": abs(int(item.get("low_pric", 0) or 0)),     # "189700"
            "close": close,                                     # "+189900"
            "volume": int(item.get("trde_qty", 0) or 0),       # "73842"
        })

    return result


async def discover(auth: KiwoomAuth, symbol: str) -> None:
    """API 응답 구조 확인용. raw JSON을 출력한다."""
    headers = await auth.build_headers(API_ID_MINUTE_CHART)
    body = {"stk_cd": symbol, "tic_scope": "1"}
    url = f"{auth.base_url}{CHART_ENDPOINT}"

    print(f"\n=== 키움 분봉 차트 API 테스트 ===")
    print(f"URL: {url}")
    print(f"api-id: {API_ID_MINUTE_CHART}")
    print(f"body: {json.dumps(body, ensure_ascii=False)}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")

        try:
            data = resp.json()
            print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        except Exception:
            print(f"Raw response:\n{resp.text[:2000]}")


async def main():
    parser = argparse.ArgumentParser(description="키움 REST API 과거 분봉 배치 수집")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                        help="종목코드 (쉼표 구분)")
    parser.add_argument("--output", default="data/minute_bars",
                        help="출력 디렉토리")
    parser.add_argument("--tick", type=int, default=1,
                        help="분 단위 (1, 3, 5, 10, 15, 30, 60)")
    parser.add_argument("--real", action="store_true",
                        help="실서버 사용 (기본: 모의서버)")
    parser.add_argument("--discover", action="store_true",
                        help="API 응답 구조 확인 모드")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # 인증 정보 로드
    app_key = os.environ.get("KIWOOM_APP_KEY", "")
    secret_key = os.environ.get("KIWOOM_SECRET_KEY", "")

    if not app_key or not secret_key:
        # keyring에서 로드 — credential.py와 동일한 서비스명 패턴
        try:
            import keyring
            for svc in ("stockvision:test@stockvision.dev", "stockvision:default"):
                ak = keyring.get_password(svc, "kiwoom_app_key")
                sk = keyring.get_password(svc, "kiwoom_secret_key")
                if ak and sk:
                    app_key, secret_key = ak, sk
                    break
        except Exception:
            pass

    if not app_key or not secret_key:
        print("ERROR: KIWOOM_APP_KEY / KIWOOM_SECRET_KEY 환경변수 또는 keyring 설정 필요")
        sys.exit(1)

    auth = KiwoomAuth(app_key, secret_key, is_mock=not args.real)
    symbols = [s.strip() for s in args.symbols.split(",")]

    if args.discover:
        await discover(auth, symbols[0])
        return

    # 수집
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_bars = 0
    for i, symbol in enumerate(symbols, 1):
        logger.info("[%d/%d] %s 수집 시작 (tick=%d분)", i, len(symbols), symbol, args.tick)
        bars = await fetch_minute_bars(auth, symbol, tick_unit=args.tick)

        if bars:
            output_file = output_dir / f"{symbol}_{args.tick}m.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(bars, f, ensure_ascii=False, indent=1)
            logger.info("[%d/%d] %s: %d건 → %s", i, len(symbols), symbol, len(bars), output_file)
            total_bars += len(bars)
        else:
            logger.warning("[%d/%d] %s: 데이터 없음", i, len(symbols), symbol)

        # 종목 간 간격
        if i < len(symbols):
            await asyncio.sleep(1.0)

    logger.info("=== 수집 완료: %d종목, 총 %d건 ===", len(symbols), total_bars)


if __name__ == "__main__":
    asyncio.run(main())
