# 분봉 데이터 수집 — MinuteBar Collection

> 작성일: 2026-03-26 | 상태: 초안

---

## 목표

멀티 타임프레임 백테스트와 분봉 기반 전략을 위한 분봉 데이터 수집 파이프라인 구축.

---

## 범위

### 포함

1. **키움 REST API 배치 수집** — 과거 1년 1분봉
2. **실시간 수집 강화** — 로컬 수집 → 클라우드 sync
3. **대신증권 Creon Plus 배치 수집** — 과거 5년 5분봉 + 2년 1분봉 (Phase 2)
4. **데이터 정규화** — 키움/대신/KIS 포맷 통일
5. **주식 분할/액면변경 보정** — adjusted price

### 미포함

- 틱 데이터 (체결건별) — 분봉으로 충분
- 해외 주식 분봉 — 국내 우선

---

## 아키텍처

```
[Phase 1: 키움 배치 + 실시간]

키움 REST API ──(배치)──→ MinuteBar (cloud DB)
     │                        ↑
     │              로컬 BarBuilder ──(sync)──→ cloud API
     │                        ↑
키움/KIS WS ──(실시간)──→ 로컬 SQLite

[Phase 2: 대신증권 추가]

Creon Plus COM ──(배치)──→ CSV ──(import)──→ MinuteBar (cloud DB)
```

---

## MC-1: 키움 REST API 과거 분봉 배치 수집

**설명**: 키움 REST API로 주요 종목 1년치 1분봉을 일괄 수집하여 cloud DB에 저장.

**수용 기준**:
- [ ] 키움 REST API 분봉 조회 엔드포인트 호출 구현
- [ ] 최신→과거 순차 블록 조회 + 자동 페이징
- [ ] 수집 대상: `get_major_symbols()` + 사용자 관심종목
- [ ] rate limit 준수 (키움 초당 제한)
- [ ] 수집 진행률 로깅
- [ ] cloud DB MinuteBar 테이블에 upsert
- [ ] 주식 분할/액면변경 보정 (adjusted price)

**파일**:
- `tools/kiwoom_minute_batch.py` (신규) — 독립 배치 스크립트 (키움 REST 직접 호출)
- `tools/import_minute_bars.py` (신규) — 수집 결과 → cloud DB 임포트

**참고**: 키움 어댑터가 `local_server/broker/kiwoom/`에만 있으므로,
배치 수집은 `tools/` 독립 스크립트로 구현. cloud_server 의존 없이 직접 DB insert.

**데이터 규모 추정**:
- 1종목 × 1년 × 380분/일 × 250거래일 = ~95,000행
- 20종목 = ~1.9M행
- 인덱스: (symbol, timestamp) — 이미 존재

**rate limit 대응**:
- 키움 API 초당 5회 제한 → 종목당 ~수분 소요
- 20종목 전체: ~1~2시간

---

## MC-2: 로컬 → 클라우드 분봉 sync

**설명**: 로컬 서버 BarBuilder가 생성하는 실시간 분봉을 cloud DB로 동기화.

**수용 기준**:
- [ ] cloud API에 분봉 ingest 엔드포인트 추가 (`POST /api/v1/bars/ingest`)
- [ ] 로컬 서버에서 heartbeat 또는 별도 task로 완성된 분봉을 cloud로 전송
- [ ] 중복 방지 (upsert by symbol + timestamp)
- [ ] 네트워크 실패 시 offline queue + 재전송

**파일**:
- `cloud_server/api/market_data.py` (수정) — ingest 엔드포인트
- `local_server/cloud/bar_sync.py` (신규) — sync worker

---

## MC-3: cloud API 분봉 조회 엔드포인트

**설명**: 프론트엔드/백테스트에서 cloud MinuteBar를 조회할 수 있는 API.

**수용 기준**:
- [ ] `GET /api/v1/stocks/{symbol}/bars` resolution 파라미터에 `1m`, `5m`, `15m`, `1h` 추가
- [ ] 분봉 → 5분봉/15분봉/1시간봉 서버사이드 집계
- [ ] 페이징 지원 (분봉은 양이 많으므로)
- [ ] 날짜 범위 필터 (start, end)

**파일**:
- `cloud_server/api/market_data.py` (수정)
- `cloud_server/services/market_repository.py` (수정) — 집계 쿼리

---

## MC-4: 대신증권 Creon Plus 배치 수집 (Phase 2)

**설명**: 대신증권 Creon Plus COM API로 5년치 5분봉 + 2년치 1분봉 수집.

**전제 조건**: 대신증권 계좌 개설

**수용 기준**:
- [ ] Creon Plus COM API 연동 스크립트 (Windows 전용)
- [ ] 5분봉 최대 ~9만건/종목, 1분봉 최대 ~18.5만건/종목
- [ ] CSV export → cloud DB import 파이프라인
- [ ] 키움 데이터와 중복 구간 정합성 검증
- [ ] rate limit 준수

**파일**:
- `tools/creon_collector.py` (신규) — Windows COM 배치 스크립트
- `tools/import_csv_bars.py` (신규) — CSV → DB 임포트

**데이터 규모 추정**:
- 5분봉: 1종목 × 5년 × 76건/일 × 1,250거래일 = ~95,000행
- 1분봉: 1종목 × 2년 × 380건/일 × 500거래일 = ~190,000행
- 20종목 전체: ~5.7M행

---

## MC-5: 주식 분할/액면변경 보정

**설명**: 과거 가격 데이터에 주식 분할/액면변경을 반영하여 adjusted price로 보정.

**수용 기준**:
- [ ] StockMaster에 분할 이력 필드 추가 (또는 별도 테이블)
- [ ] 분할 이전 가격을 비율로 보정하는 함수
- [ ] 배치 수집 시 자동 보정 옵션
- [ ] 보정 여부 플래그 (adjusted / raw)

**적용 범위**: 키움/대신 배치 데이터만 해당 (yfinance는 `auto_adjust=True`로 이미 보정됨)

**참고**: 삼성전자 2018-05-04 50:1 분할, 카카오 2021-04-15 5:1 분할 등

---

## 데이터 보존 정책

| 해상도 | 보존 기간 | 비고 |
|--------|----------|------|
| 1분봉 | 2년 | 이후 5분봉으로 집계 후 원본 삭제 |
| 5분봉 | 5년 | 장기 백테스트용 |
| 15분봉/1시간봉 | 온디맨드 집계 | 저장 안 함, 쿼리 시 계산 |
| 일봉 | 영구 | 기존 DailyBar |

---

## 장외시간 처리

| 시간대 | 처리 |
|--------|------|
| 08:30~09:00 (동시호가) | 수집하되 `is_auction=True` 플래그 |
| 09:00~15:20 (정규장) | 정상 수집 |
| 15:20~15:30 (장마감 동시호가) | 수집하되 `is_auction=True` 플래그 |
| 15:30~16:00 (시간외) | 수집 안 함 (옵션) |
