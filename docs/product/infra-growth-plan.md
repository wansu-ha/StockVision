# 인프라 성장 계획 (초안)

> 작성일: 2026-03-26 | 상태: 초안 — 추후 재조사 시 참고용

---

## 현재 인프라

| 구성 | 서비스 | 플랜 | 제한 |
|------|--------|------|------|
| API 서버 | Render | Free | 512MB RAM, 15분 비활성 시 sleep |
| DB | Render PostgreSQL | Free | 1GB, **30일 만료** |
| 프론트엔드 | Vercel | Free | 충분 |
| 로컬 서버 | 사용자 PC | - | 제한 없음 |

---

## 문제

1. **DB 30일 만료** — 분봉 데이터 축적 불가
2. **분봉 데이터 용량** — 20종목 1년 ~100MB, 전 종목 ~12GB/년
3. **백테스트 CPU** — 분봉 5년 루프 시 15초+, 동시 요청 시 공유 CPU 부족

---

## 필요한 것 (우선순위순)

### 1. 영속 PostgreSQL (출시 전 필수)
- 현재 Render Free DB는 30일 만료 → 분봉/백테스트 데이터 유실
- **후보**: Supabase Free (500MB), Neon Free (512MB), Render Starter ($7/월)
- **기준**: 무료 → 유료 전환 매끄러운 곳, PostgreSQL 호환
- **코드 변경**: `DATABASE_URL` 환경변수만 교체

### 2. 시계열 DB 또는 파티셔닝 (유저 100명+ 시)
- 분봉 데이터가 수천만 행 넘으면 일반 PostgreSQL 쿼리 성능 저하
- **후보**: TimescaleDB (PostgreSQL 확장), InfluxDB, QuestDB
- **기준**: 기존 SQLAlchemy 호환 여부, 관리 비용
- TimescaleDB는 PostgreSQL 위에 올리므로 마이그레이션 최소

### 3. 데이터 수집 분리 서버 (전 종목 수집 시)
- 전 종목(2,400개) 실시간 분봉 수집은 API 서버와 분리 필요
- 수집 봇 + 뉴스/커뮤 크롤러 + 시계열 DB를 독립 서버로
- **후보**: 별도 VPS ($10~20/월), Railway, Fly.io
- **시점**: 유저 규모 또는 수집 종목 수가 100+ 넘을 때

### 4. 백테스트 전용 워커 (동시 사용자 10명+ 시)
- 백테스트는 CPU 집약적 — API 서버와 동일 프로세스에서 돌리면 다른 요청 블로킹
- **후보**: 별도 워커 프로세스 (Celery + Redis), 또는 서버리스 함수
- **시점**: 동시 백테스트 요청이 잦아질 때

---

## 성장 단계별 예상 비용

| 단계 | 월 비용 | 구성 |
|------|--------|------|
| 개발/테스트 (지금) | $0 | Render Free + Render Free DB |
| 출시 전 (DB 전환) | $0~7 | Render Free + 영속 DB |
| 출시 초기 (~50유저) | ~$30 | Render Starter + Supabase Pro |
| 성장기 (~500유저) | ~$80 | Render + 수집 VPS + TimescaleDB |
| 전 종목 수집 | ~$150+ | 분리 서버 + 대용량 DB |

---

## 키움 REST API 분봉 조회 — 확인된 사항

```
엔드포인트: POST /api/dostk/chart
api-id: ka10080
필수 파라미터: stk_cd, tic_scope (분 단위), upd_stkpc_tp (수정주가)
응답: 900건/페이지, cont-yn + next-key 페이징
필드: cur_prc, open_pric, high_pric, low_pric, trde_qty, cntr_tm, acc_trde_qty
가격: 부호 접두사 ("+189900", "-189000") → abs() 필요
모의서버 검증 완료 (2026-03-26)
```

**rate limit**: 429 에러 확인됨 (연속 호출 시). ~1초 간격 권장.
**데이터 보유**: ~1년 (커뮤니티 보고 기준, 공식 미확인)

---

## 대신증권 Creon Plus — 조사 필요 사항

- 계좌 개설 필요
- Windows COM API (ActiveX)
- 1분봉 ~2년, 5분봉 ~5년 보유
- rate limit 미확인
- 배치 스크립트 별도 개발 필요 (`tools/creon_collector.py`)
