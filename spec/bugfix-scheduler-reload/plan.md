# 자동매매 규칙 즉시 반영 — 구현 계획서

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/api/trading.py` | `update_rule`, `create_rule`, `delete_rule`에 `reload_rules()` 호출 추가 |

## 단계별 구현

### Step 1: trading.py에 스케줄러 import 추가

**변경 위치**: `trading.py` 상단 import 섹션

```python
from app.services.auto_trade_scheduler import get_auto_scheduler
```

### Step 2: `update_rule` 엔드포인트에 reload 추가

**변경 위치**: `trading.py:351-364`

```python
@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: int, req: RuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(AutoTradingRule).filter(AutoTradingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    # 스케줄러 즉시 동기화 (미시작 상태면 스킵)
    scheduler = get_auto_scheduler()
    if scheduler._started:
        scheduler.reload_rules()

    return {"success": True, "data": _rule_to_dict(rule), "count": 1}
```

### Step 3: `create_rule` 엔드포인트에 reload 추가

**변경 위치**: `trading.py` create_rule 핸들러 (db.commit() 직후)

```python
    db.commit()
    db.refresh(rule)

    scheduler = get_auto_scheduler()
    if scheduler._started:
        scheduler.reload_rules()

    return {"success": True, "data": _rule_to_dict(rule), "count": 1}
```

### Step 4: `delete_rule` 엔드포인트에 reload 추가

**변경 위치**: `trading.py` delete_rule 핸들러 (db.commit() 직후)

```python
    db.delete(rule)
    db.commit()

    scheduler = get_auto_scheduler()
    if scheduler._started:
        scheduler.reload_rules()

    return {"success": True, "data": {"id": rule_id, "deleted": True}, "count": 1}
```

## 검증

- 백엔드 서버 실행 중 규칙 활성화 PATCH 직후 스케줄러 잡 목록 확인
- `scheduler.get_jobs()` 로그로 잡 등록/해제 확인
- 스케줄러 미시작 환경(테스트)에서 PATCH가 500 없이 성공하는지 확인
