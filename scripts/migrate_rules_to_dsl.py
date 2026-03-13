"""JSON 조건 → DSL 마이그레이션 스크립트.

기존 buy_conditions/sell_conditions JSON을 DSL script 텍스트로 변환.
dry-run 모드(기본): 변환 결과만 출력, DB 수정 없음.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sv_core.parsing import parse, DSLError


# ── JSON → DSL 변환 ──

# JSON field → DSL 식별자 매핑
FIELD_MAP: dict[str, str] = {
    "price": "현재가",
    "current_price": "현재가",
    "volume": "거래량",
    "volume_ratio": "거래량",
    "rsi_14": "RSI(14)",
    "ema_20": "EMA(20)",
    "ema_60": "EMA(60)",
    "macd": "MACD()",
    "macd_signal": "MACD_SIGNAL()",
    "bb_upper": "볼린저_상단(20)",
    "bb_lower": "볼린저_하단(20)",
}


def condition_to_dsl(cond: dict) -> str:
    """단일 JSON 조건 → DSL 표현식."""
    field = cond.get("field", cond.get("variable", ""))
    op = cond.get("operator", "")
    value = cond.get("value", 0)

    dsl_field = FIELD_MAP.get(field, field)
    return f"{dsl_field} {op} {value}"


def conditions_to_dsl(conds: dict | None, operator: str = "AND") -> str:
    """JSON 조건 세트 → DSL 식."""
    if not conds:
        return "true"

    items = conds.get("conditions", [])
    if not items:
        return "true"

    op = conds.get("operator", operator)
    parts = [condition_to_dsl(c) for c in items]
    return f" {op} ".join(parts)


def rule_to_dsl(rule: dict) -> str:
    """규칙 dict → DSL script 텍스트."""
    buy_expr = conditions_to_dsl(rule.get("buy_conditions"))
    sell_expr = conditions_to_dsl(rule.get("sell_conditions"))
    return f"매수: {buy_expr}\n매도: {sell_expr}"


# ── 메인 ──

def migrate(rules: list[dict], dry_run: bool = True) -> list[dict]:
    """규칙 목록 마이그레이션.

    Returns:
        변환 결과 목록: [{id, name, script, valid, error}]
    """
    results = []
    for rule in rules:
        rule_id = rule.get("id", "?")
        name = rule.get("name", "")

        # 이미 script가 있으면 스킵
        if rule.get("script"):
            results.append({
                "id": rule_id, "name": name,
                "script": rule["script"], "valid": True, "error": None,
                "skipped": True,
            })
            continue

        # JSON → DSL 변환
        try:
            script = rule_to_dsl(rule)
        except Exception as e:
            results.append({
                "id": rule_id, "name": name,
                "script": None, "valid": False, "error": f"변환 실패: {e}",
                "skipped": False,
            })
            continue

        # 파싱 검증
        try:
            parse(script)
            valid = True
            error = None
        except DSLError as e:
            valid = False
            error = str(e)

        results.append({
            "id": rule_id, "name": name,
            "script": script, "valid": valid, "error": error,
            "skipped": False,
        })

        if not dry_run and valid:
            rule["script"] = script

    return results


def main():
    parser = argparse.ArgumentParser(description="JSON → DSL 마이그레이션")
    parser.add_argument("--input", "-i", help="규칙 JSON 파일 (없으면 stdin)")
    parser.add_argument("--apply", action="store_true", help="실제 변환 적용 (기본: dry-run)")
    args = parser.parse_args()

    # 입력 읽기
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            rules = json.load(f)
    else:
        rules = json.load(sys.stdin)

    if not isinstance(rules, list):
        rules = [rules]

    # 마이그레이션
    results = migrate(rules, dry_run=not args.apply)

    # 결과 출력
    ok_count = sum(1 for r in results if r["valid"])
    skip_count = sum(1 for r in results if r.get("skipped"))
    fail_count = sum(1 for r in results if not r["valid"])

    print(f"\n{'=' * 50}")
    print(f"총 {len(results)}건: 성공 {ok_count}, 스킵 {skip_count}, 실패 {fail_count}")
    print(f"모드: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"{'=' * 50}\n")

    for r in results:
        status = "SKIP" if r.get("skipped") else ("OK" if r["valid"] else "FAIL")
        print(f"[{status}] #{r['id']} {r['name']}")
        if r["script"]:
            for line in r["script"].split("\n"):
                print(f"  {line}")
        if r["error"]:
            print(f"  ERROR: {r['error']}")
        print()

    if args.apply:
        json.dump(rules, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
