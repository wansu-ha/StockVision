# 자동매매 규칙 즉시 반영 — 기능 명세서

## 목표

자동매매 규칙(활성화/비활성화 포함)이 변경될 때 서버 재시작 없이 즉시 스케줄러에 반영되도록 한다.

## 문제

### W-9: 규칙 PATCH 후 스케줄러 미갱신

`PATCH /api/v1/trading/rules/{rule_id}` 엔드포인트가 DB만 업데이트하고 실행 중인 스케줄러에는 변경을 알리지 않는다.

```python
# backend/app/api/trading.py:351-364 — 현재 코드
@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: int, req: RuleUpdate, db: Session = Depends(get_db)):
    # ... DB 업데이트 ...
    db.commit()
    db.refresh(rule)
    return {"success": True, "data": _rule_to_dict(rule), "count": 1}
    # ← reload_rules() 호출 없음
```

결과:
- 규칙 비활성화 → 스케줄러 잡은 계속 실행됨
- 규칙 활성화 → 스케줄러 잡이 등록되지 않아 자동매매 안 됨
- 서버 재시작 시에만 `start()`에서 활성 규칙을 재로드

`AutoTradeScheduler.reload_rules()`는 이미 구현되어 있으나 호출되지 않고 있다 (`auto_trade_scheduler.py:56-68`).

## 요구사항

### FR-1: 규칙 변경 후 스케줄러 즉시 동기화

- FR-1.1: `PATCH /rules/{rule_id}` 응답 전에 `reload_rules()` 호출
- FR-1.2: 스케줄러가 시작되지 않은 경우(테스트 환경 등) 에러 없이 스킵
- FR-1.3: `POST /rules` (신규 생성) 시에도 동일하게 reload 적용
- FR-1.4: `DELETE /rules/{rule_id}` 시에도 동일하게 reload 적용

### FR-2: 스케줄러 의존성 주입

- FR-2.1: `get_auto_scheduler()` 싱글톤을 FastAPI Depends로 라우터에 주입
- FR-2.2: 스케줄러가 미시작(`_started == False`) 상태면 reload 스킵

## 수용 기준

- [ ] 규칙 활성화 직후 다음 크론 시각에 자동매매 잡이 실행됨
- [ ] 규칙 비활성화 직후 스케줄러 잡 목록에서 제거됨
- [ ] 신규 규칙 생성 시 즉시 잡 등록됨
- [ ] 규칙 삭제 시 즉시 잡 제거됨
- [ ] 스케줄러 미시작 환경에서 PATCH 요청이 500 에러 없이 성공
