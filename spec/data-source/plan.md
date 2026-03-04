# 데이터 소스 구현 계획서 (data-source)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: 현행 유지 + Phase 3 키움 연동 시 전환

---

## 0. 현황 및 방향

**현재 사용**: yfinance (무료, 미국 주식 중심)
**Phase 3 목표**: 한국 주식 실시간 시세는 키움 COM API 직접 수신

Phase 3에서 실시간 데이터는 `kiwoom-integration`에서 처리하므로, 이 spec의 구현 범위는 **yfinance 유지 + 데이터 품질 개선**이다.

---

## 1. 구현 단계

### Step 1 — yfinance 안정화 (현행 유지)

**목표**: 현재 yfinance 기반 데이터 수집 안정화 + 에러 처리 강화

파일: `backend/app/services/data_ingestion.py` (기존)

```
개선 사항:
- 야후 API 일시 오류 → 재시도 (3회, 지수 백오프)
- 한국 심볼 처리: yfinance 형식 (ex. 005930.KS)
- 결측 데이터 탐지 + 경고 로그
- 수집 실패 시 마지막 정상 데이터 유지 (silent fail 방지)
```

**검증:**
- [ ] AAPL, 005930.KS 각 100일치 수집 성공
- [ ] 야후 서버 오류 시 재시도 후 정상 복귀
- [ ] 결측 일자 감지 로그 확인

### Step 2 — 컨텍스트 데이터 소스 (Phase 3 클라우드)

**목표**: 클라우드 서버에서 `GET /api/context` 응답에 필요한 시장 지표 계산

참조: `spec/context-cloud/spec.md`

데이터 계산 대상:
- KOSPI/KOSDAQ 지수 일봉 (yfinance `^KS11`, `^KQ11`)
- 시장 RSI, 20일 변동성
- 섹터 모멘텀 (ETF 기준 근사치)

파일: `backend/app/services/market_context.py` (신규)

```python
def compute_market_context(date: date) -> dict:
    """장 마감 후 1회 호출 → context API 응답 데이터 생성"""
    ...
```

**검증:**
- [ ] `GET /api/context` 응답에 RSI, 변동성 포함 확인
- [ ] 장 마감(15:30 KST) 이후 계산 완료 확인
- [ ] 계산 실패 시 이전 캐시 유지

### Step 3 — 키움 실시간 연동 (Phase 3 로컬)

> Phase 3 로컬 서버 구현 시 별도 처리. `spec/kiwoom-integration/plan.md` 참조.

실시간 시세 수신은 로컬 서버가 키움 COM API에서 직접 처리 → 클라우드 서버로 시세 업로드 금지 (G5 제5조③).

---

## 2. 파일 목록

| 파일 | 변경 |
|------|------|
| `backend/app/services/data_ingestion.py` | 재시도 로직, 결측 탐지 추가 |
| `backend/app/services/market_context.py` | 신규 — 시장 지표 계산 |
| `backend/app/api/context.py` | 신규 — `GET /api/context` 엔드포인트 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — yfinance 재시도 + 결측 탐지 강화` |
| 2 | `feat: Step 2 — market_context 계산 서비스 + context API` |
