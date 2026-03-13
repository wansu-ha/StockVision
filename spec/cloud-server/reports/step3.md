# Step 3 보고서: 전략 규칙 CRUD

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/models/rule.py` | TradingRule 모델 (version, UniqueConstraint) |
| `cloud_server/core/validators.py` | 조건 JSON 형식 검증 |
| `cloud_server/services/rule_service.py` | 규칙 CRUD 비즈니스 로직 |
| `cloud_server/api/rules.py` | 규칙 API 라우터 |

### API 엔드포인트 (/api/v1/rules)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/` | GET | 내 규칙 목록 + 최신 version |
| `/` | POST | 규칙 생성 (version=1) |
| `/{id}` | GET | 규칙 상세 |
| `/{id}` | PUT | 규칙 수정 (version++) |
| `/{id}` | DELETE | 규칙 삭제 (물리 삭제) |

### 조건 JSON 검증 (validators.py)

유효한 형식:
```json
{
  "operator": "AND",
  "conditions": [
    {"type": "indicator", "field": "rsi_14", "operator": "<=", "value": 30}
  ]
}
```

검증 항목:
- operator: AND | OR
- type: indicator | context | price
- field: 비어있지 않은 문자열
- operator: < > <= >= == !=
- value: 숫자 (int | float)

### 동기화 지원

- `GET /api/v1/rules` 응답에 `version` 포함 → 하트비트 응답의 rules_version과 비교
- `PUT /api/v1/rules/{id}` 성공 시 version 자동 증가

## 검증 결과

- [x] TradingRule 모델 (UniqueConstraint user_id+name)
- [x] 조건 JSON 검증 (유효/무효 케이스)
- [x] 사용자 격리 (user_id 필터링으로 다른 유저 접근 불가)
- [x] version 증가 로직
