# 코스콤 오픈플랫폼 연동 명세서 작성 완료

**작성일**: 2026-03-04
**상태**: 초안 완료
**위치**: `/d/Projects/StockVision/spec/koscom-integration/spec.md`

---

## 작성 내용 요약

### 1. 핵심 정의
- **목적**: StockVision 사용자의 실제 증권 계좌 정보 안전하게 연동
  - 실시간 잔고 조회
  - 거래 내역 조회
  - 자산별 구성 모니터링

- **핵심 가치**:
  - 합법적 데이터 경로 (코스콤 공식 등록)
  - 키움증권 제5조③ (시세 중계 금지) 규정 우회
  - 공식 핀테크기업 지위로 신뢰성 강화

### 2. 코스콤 오픈플랫폼 구조
- **인증 방식**: OAuth 2.0 (Authorization Code Flow)
- **토큰 유효기간**: Access Token 1시간, Refresh Token 12개월 (동의 유효기간)
- **권한 범위**:
  - readaccount (계좌 조회)
  - readtrade (거래 내역)
  - readasset (자산 구성)
- **데이터 제공 경로**: 증권사 API → 코스콤 브릿지 → StockVision 백엔드

### 3. 등록 절차 (핀테크기업 등록)
**예상 소요 기간**: 2주 (심사)

5단계 절차:
1. 회사 정보 + 서비스 정보 준비
2. 코스콤 사이트에서 신청서 작성
3. 서류 심사 (1~2주)
4. 심사 통과 후 Client ID/Secret 발급
5. 개발팀 토큰 검증 및 테스트

**필수 제출 문서**:
- 개인정보처리방침
- 이용약관
- 서비스 보안 정책서
- API 사용 계획서

### 4. 제공 데이터 (제6조)
4가지 API 엔드포인트:

| 데이터 | 조회 주기 | 활용 | 지연도 |
|--------|---------|------|-------|
| 실시간 잔고 | 3시간 | 백테스팅과 실제 자산 비교 | 1분 이내 |
| 거래 내역 | 1일 1회 | 거래 로그 시각화 + 수익률 계산 | 당일 종가 후 |
| 자산 구성 | 3시간 | 포트폴리오 비율 분석 | 1분 이내 |
| 관심종목 | 1주 1회 | 추천 종목과의 연관성 검토 | 즉시 |

### 5. 사용자 동의 플로우
**초기 연동 (First-time Setup)**:
```
사용자 "계좌 연동하기" 클릭
  → 코스콤 OAuth 페이지로 리다이렉트 (본인인증)
  → 백엔드가 Authorization Code로 Token 교환
  → DB에 암호화 저장 (Refresh Token 12개월 유효)
  → Dashboard 리로드
```

**토큰 갱신 (Daily Batch)**:
- 매일 00시에 배치 작업 실행
- 모든 사용자의 refresh_token 갱신
- 갱신 실패 시 사용자에게 재동의 알림

**동의 만료 (연 1회)**:
- consent_expires_at 30일 전부터 Dashboard 배너 표시
- 사용자가 "동의 갱신하기" 클릭하면 재인증

### 6. 기술 요구사항

#### 백엔드 변경사항
**신규 DB 테이블**:
- `koscom_accounts`: 사용자별 OAuth 토큰 저장 (암호화)
- `account_data_cache`: 조회된 데이터 캐싱 (TTL 기반)

**신규 API 라우터** (`app/api/koscom.py`):
- `POST /api/v1/koscom/auth/start` — OAuth URL 생성
- `POST /api/v1/koscom/auth/callback` — Token 교환 및 저장
- `POST /api/v1/koscom/auth/revoke` — 동의 취소
- `GET /api/v1/koscom/account/balance` — 잔고 조회
- `GET /api/v1/koscom/account/trades` — 거래 내역 조회
- `GET /api/v1/koscom/account/allocation` — 자산 구성 조회
- `GET /api/v1/koscom/account/status` — 동의 상태 조회

**백그라운드 배치**:
- 매일 00:00에 모든 사용자 토큰 갱신

**암호화 서비스**:
- AES-256 기반 Refresh Token 암호화 저장

#### 프론트엔드 변경사항
**신규 페이지**:
- `src/pages/KoscomAuth.tsx` — OAuth 콜백 처리
- `src/pages/AccountSettings.tsx` — 계좌 연동 설정 UI

**기존 컴포넌트 수정**:
- `src/components/Portfolio.tsx` — 실제 계좌 탭 추가
- Dashboard에 동의 만료 배너 표시

**신규 서비스 + 타입**:
- `src/services/koscomApi.ts` — API 클라이언트
- `src/types/koscom.ts` — TypeScript 타입 정의

#### 보안 요구사항
1. **토큰 저장**: AES-256 암호화 필수
2. **HTTPS**: Redirect URI는 반드시 HTTPS
3. **State Parameter**: CSRF 방지를 위한 state 검증
4. **Rate Limiting**: 분당 100회 호출 제한 (캐싱으로 최소화)
5. **개인정보보호**: 계좌번호 마스킹, 로그에는 끝 4자리만

### 7. 미결 사항 (TBD)
| 항목 | 담당 |
|------|------|
| 코스콤 핀테크기업 등록 비용 여부 | 운영팀 |
| 데이터 SLA (응답 시간 보장) | 기술팀 |
| 각 증권사별 API 응답 시간 | 기술팀 |
| 과거 거래 내역 조회 기간 제한 | 기술팀 |
| 실시간 Push 가능 여부 | 기술팀 |

### 8. 순차 의존성 (Implementation Order)
```
Step 1: 코스콤 핀테크기업 등록 신청 (2주 소요)
Step 2: Client ID/Secret 발급 받음
Step 3: 백엔드 OAuth 라우터 구현 + 테스트
Step 4: 프론트엔드 Auth/Dashboard UI 구현
Step 5: End-to-End 테스트 (Sandbox 환경)
Step 6: 운영 배포
```

### 9. 향후 확장 (Phase 4+)
- **자동매매 실행**: KIS Open API 별도 등록
- **실시간 알림**: 시세 변동 시 푸시/이메일
- **포트폴리오 최적화**: 리밸런싱 제안
- **세금 계산**: 기간별 손익 통계 + 세무 보고서

---

## 명세서 구조

```
spec.md
├─ 1. 개요 (목적, 가치, 범위, 미포함 항목)
├─ 2. 코스콤 오픈플랫폼 구조 (조직도, 인증방식, 데이터 경로)
├─ 3. 등록 절차 (사전 준비, 신청 5단계, 필수 문서)
├─ 4. 제공 데이터 (4가지 API 스펙 + 활용)
├─ 5. 사용자 동의 플로우 (초기 연동, 토큰 갱신, 동의 만료)
├─ 6. 기술 요구사항 (DB 테이블, 라우터, UI, 보안)
├─ 7. 미결 사항 (TBD 항목, 의존성)
└─ 8. 참고 자료 (링크)
```

---

## 완료 체크리스트

- [x] 디렉토리 구조 생성 (`spec/koscom-integration/reports/`)
- [x] spec.md 파일 작성 완료
- [x] 8개 섹션 모두 포함
- [x] 실제 구현을 위한 구체적 요구사항 정의
- [x] 보안, 규제, 데이터 정책 명확화
- [x] 프론트엔드/백엔드 기술 요구사항 분리 명시
- [x] 향후 Phase 3 plan/reports 작성 준비 완료

---

## 다음 단계

1. **운영팀**: 코스콤 핀테크기업 등록 신청 (TBD 항목 확인 후)
2. **기술팀**: `plan.md` 작성 (Phase 3 로드맵)
3. **개발**: Step 3부터 시작 (OAuth 백엔드 구현)

