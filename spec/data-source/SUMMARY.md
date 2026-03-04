# 데이터 소스 전략 명세서 — 완성 요약

## 개요
StockVision 프로젝트의 **데이터 소스 전략** 명세서가 완성되었습니다.
전체 865줄로 구성된 포괄적인 문서입니다.

---

## 파일 위치
```
d:/Projects/StockVision/spec/data-source/spec.md
```

---

## 핵심 내용

### 1. 데이터 소스 5가지 비교
| 소스 | 현황 | 비용 | 한국주식 | 실시간 | 추천 |
|------|------|------|---------|--------|------|
| **yfinance** | ✅ 사용 중 | 무료 | ⚠️ 중간 | ❌ | Phase 2 |
| **KRX API** | ❌ 미추가 | 무료 | ✅ 우수 | ❌ | Phase 3 |
| **키움 OpenAPI+** | ⚠️ 스텁 | 무료 | ✅ 우수 | ✅ | Phase 4 |
| **코스콤** | ❌ 미추가 | ~50K/월 | ✅ 우수 | ✅ | Phase 4 |
| **Alpha Vantage** | ❌ | 무료~$8/월 | ❌ 미지원 | ⚠️ | 미권장 |

### 2. Phase별 권장 전략

#### Phase 2 (현재, 무변경)
- ✅ yfinance 계속 사용 (일봉 데이터)
- ✅ 기술적 지표 직접 계산
- ⏳ KRX API 추가 고려 (데이터 검증용)
- **비용**: $0

#### Phase 3 (한국 주식 품질 향상)
- 📌 **KRX를 주 소스로 전환** (일봉 OHLCV)
- 🔌 로컬 브릿지 (키움 분봉/실시간)
- 📊 데이터 애그리게이터 구현
- **비용**: $0 + 로컬 브릿지 운영

#### Phase 4 (완전성, 실거래 지원)
- 💳 코스콤 구독 (재무정보, 실시간)
- 🔐 키움 실거래 지원
- 📈 거시경제 지표 통합
- **비용**: ~50K/월

### 3. 법적 제약 (중요)

#### ⚠️ yfinance
- Yahoo Finance ToS에서 상업용 사용 제약 모호
- 개발/테스트 단계에서는 관대
- **상용화 시**: 자체 API 전환 필수

#### ⚠️ 키움증권 (G5 제5조③)
```
금지: 백엔드 서버에서 시세 조회 후
      다수 사용자에게 중계

허용: 각 사용자 PC의 로컬 브릿지에서 직접 조회
```
- **SaaS 모델에서 로컬 브릿지 필수**
- 참고: `spec/kiwoom-integration/spec.md`

#### ✅ KRX (공공 API)
- 무료, 상업용 명시 OK
- 저작권 표시 필수
- **가장 안전한 선택**

#### ✅ 코스콤
- 유료이지만 법적으로 명확
- 재판매 금지 (SaaS 분석용 O)

### 4. 기술 구현 계획

**Phase 3 아키텍처**:
```
DataAggregator
  ├─ YFinanceDataSource (미국 주식)
  ├─ KRXDataSource (한국 일봉) ← 신규
  ├─ KiwoomDataSource (분봉, 로컬 브릿지)
  └─ TechnicalIndicators (지표 계산)
```

**구현 순서**:
1. KRX API 통합
2. 데이터 소스 추상화 (interface)
3. 데이터 애그리게이터 (우선순위 병합)
4. 품질 모니터링 (수집 성공률, 신선도)

---

## 주요 결정사항

### 즉시 적용 (No Change Required)
- ✅ yfinance 계속 사용 → Phase 2 목표 충분
- ⏳ KRX API 추가 검토 → 선택사항

### 중기 계획 (Phase 3)
- 📌 **KRX를 주 소스로 전환**
- 🔌 데이터 소스 추상화 & 애그리게이터
- 📊 로컬 브릿지 초안

### 장기 계획 (Phase 4)
- 💳 코스콤 구독
- 🔐 키움 실거래 연동
- 📈 거시경제 지표 통합

---

## 미결 사항 (Action Items)

### 아키텍처 결정
- [ ] KRX API 우선순위 (yfinance vs KRX)
- [ ] 코스콤 구독 시기 (Phase 3 vs 4)
- [ ] 로컬 브릿지 개발 (별도 프로젝트 vs 통합)

### 기술 검증
- [ ] yfinance 한국 주식 품질 측정
- [ ] KRX API 안정성 & 성능 테스트
- [ ] 키움 G5 제5조③ 법률 자문

### 문서화
- [ ] KRX API 호출 가이드
- [ ] 데이터 신선도 모니터링 매뉴얼
- [ ] 로컬 브릿지 설치 가이드

### 법적 컴플라이언스
- [ ] 키움증권 사전 문의 (G5 제5조 해석)
- [ ] 이용약관 업데이트 (데이터 출처 명시)

---

## 참고 정보

### 현재 구현 경로
| 영역 | 파일 | 상태 |
|------|------|------|
| 데이터 수집 | `backend/app/services/data_collector.py` | ✅ yfinance만 |
| 데이터 서빙 | `backend/app/services/stock_data_service.py` | ✅ 캐싱 포함 |
| 기술적 지표 | `backend/app/services/technical_indicators.py` | ✅ 완성 |
| Rate Limit | `backend/app/core/rate_limit_monitor.py` | ✅ 완성 |
| 키움 클라이언트 | `backend/app/services/kiwoom_client.py` | ⚠️ 스텁 |

### 관련 문서
- 📄 `docs/architecture.md` — 전체 아키텍처
- 📄 `spec/kiwoom-integration/spec.md` — 키움 연동 & 로컬 브릿지
- 📄 `spec/virtual-auto-trading/spec.md` — 가상 거래 엔진

---

## 완성 메타데이터
- **작성일**: 2026-03-04
- **상태**: 초안 (검토 필요 전 완성)
- **길이**: 865줄 (spec.md 본문)
- **버전**: 1.0

**다음 단계**:
1. 팀 검토 & 피드백
2. 법률 자문 (키움 G5 제5조)
3. Phase 3 기획서 작성 시 이 명세서 기반으로 상세 계획 수립
