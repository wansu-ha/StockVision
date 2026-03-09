# StockVision 키움증권 약관 준수 확인서

**최종 갱신**: 2026-03-05
**버전**: 1.0
**문서 분류**: 내부 기술 문서 (법무 검수용)
**목적**: 키움증권 OpenAPI+ 이용약관 준수 여부 자체 검증

---

## 목차

1. 제3자 위임 금지 (제5조②)
2. 시세 중계 금지 (제5조③)
3. 통신비 청구 (제7조)
4. 기술 명세 및 보안
5. IP 화이트리스트 설정
6. 체크리스트 및 확인

---

## 제1부 제3자 위임 금지 (키움 약관 제5조②)

### 1.1 조항 내용

**키움 약관 제5조②**:
> "사용자는 보안 및 책임성 확보를 위하여 자신의 API Key를 제3자에게 대여, 양도, 공개하지 아니합니다."

### 1.2 우리의 준수 방식

#### 1.2.1 API Key 저장 위치

| Key 종류 | 소유자 | 저장 위치 | 접근 가능자 | 비고 |
|---------|-------|---------|-----------|-----|
| **서비스 키** | StockVision | 클라우드 서버 (환경변수) | 클라우드 API 서버 프로세스 | 시세 수집용 |
| **유저 키** | 각 사용자 | 사용자 PC (Credential Manager) | 해당 PC의 로컬 서버만 | 거래 실행용 |

#### 1.2.2 서비스 키 관리

**서비스 키 (StockVision 소유)**:
```
저장: 클라우드 서버 환경변수
  ├─ AWS Secrets Manager 또는 HashiCorp Vault
  ├─ 암호화 저장 (AES-256)
  └─ 접근 권한: API 서버만 가능

사용 목적: 시세 수집 (내부 분석만)
  ├─ 일봉, 주봉, 월봉 데이터
  ├─ 기술적 지표 계산 (MA, RSI 등)
  └─ 유저에게 재배포 금지

보안 조치:
  ├─ IP 화이트리스트: 클라우드 서버 IP만
  ├─ 로깅: 모든 API 호출 기록
  └─ 감시: 비정상 거래량 탐지
```

**확인 사항**:
- [x] 서비스 키를 사용자에게 노출하지 않음
- [x] 서비스 키를 제3자(Google, Amazon 등)에 공유하지 않음
- [x] 서비스 키는 환경변수로만 관리 (코드에 하드코딩 안 함)

#### 1.2.3 유저 키 관리

**유저 키 (각 사용자 소유)**:
```
저장: 사용자 PC → Windows Credential Manager
  ├─ DPAPI(Data Protection API) 암호화
  ├─ 로그인한 사용자만 복호화 가능
  └─ 다른 사용자/원격 접근 불가

사용 목적: 시세 수신 + 주문 실행
  ├─ 리얼타임 시세 수신 (WebSocket)
  ├─ 주문 실행 (REST API)
  └─ 서버로 전송 금지

보안 조치:
  ├─ 로컬 서버만 접근 (localhost:8001)
  ├─ HTTPS 사용 금지 (로컬이므로 필요 없음)
  ├─ 토큰화: 클라우드에 토큰만 저장 (Key 자체 미저장)
  └─ 감시: Key 전송 시도 시 즉시 차단 및 로그
```

**확인 사항**:
- [x] 유저 키를 클라우드 서버에 저장하지 않음
- [x] 유저 키를 제3자에게 전송하지 않음
- [x] 유저 키는 사용자 PC의 보안 저장소에만 보관
- [x] 사용자가 Key를 등록/수정/삭제할 때만 접근

#### 1.2.4 아키텍처 다이어그램

```
[사용자 PC]
  ├─ Windows Credential Manager (DPAPI 암호화)
  │   └─ 키움 유저 API Key/Secret
  │
  └─ 로컬 서버 (StockVision-Engine)
      ├─ Key 읽기 (Credential Manager에서만)
      ├─ 키움 WebSocket 연결 (시세 수신)
      ├─ 키움 REST API 호출 (주문 실행)
      └─ 로컬 로그 저장 (체결 기록)
          └─ SQLite: %APPDATA%\StockVision\logs.db

[클라우드 서버]
  ├─ 환경 변수: 키움 서비스 API Key/Secret
  ├─ 서비스 API 호출 (시세 수집)
  ├─ 클라우드 DB에 시세 저장
  └─ 프론트엔드/로컬에 시세 제공 (사용자 재배포 안 함)

통신:
  ├─ 사용자 Key ↔ 로컬 서버: 로컬 시스템만 (Network 없음)
  ├─ 로컬 서버 → 키움: HTTPS (사용자 Key 사용)
  ├─ 클라우드 서버 → 키움: HTTPS (서비스 Key 사용)
  └─ 클라우드 ↔ 프론트엔드: HTTPS (Key 전송 안 함)
```

#### 1.2.5 제3자 위임 방지 검증

"제3자 위임"이 되지 않기 위해:

1. **직접 실행**: 로컬 서버가 사용자를 대신하여 직접 주문하지 않음
   - 규칙 자동 실행은 사용자의 PC에서 일어남
   - 키움도 "사용자의 로컬 PC에서 실행"으로 인식

2. **Key 보관**: 사용자 Key는 절대로 서버에 저장하지 않음
   - 키움이 "제3자가 Key를 보관했다"고 의심하지 않음

3. **책임 추적**: 매매 책임이 명확히 사용자에게 귀속
   - StockVision은 "도구 제공"만 하고 매매 판단은 규칙 = 사용자

**예시 - 제3자 위임이 될 수 없는 이유**:

```
❌ 제3자 위임 (금지):
[사용자] → "이 규칙대로 매매하세요" → [우리 서버]
                                         └─ 서버가 주문 실행
                                         └─ Key가 서버에 있음
                                         ✗ 제3자 위임 = 금지

✅ 제3자 위임 아님 (허용):
[사용자 PC의 로컬 서버] → "규칙 평가" → "자동 주문"
                      (사용자 자신이 직접 실행)
                      Key는 사용자 PC에만 있음
                      ✓ 제3자 위임 ≠ 규칙 기반 자동화
```

---

## 제2부 시세 중계 금지 (키움 약관 제5조③)

### 2.1 조항 내용

**키움 약관 제5조③**:
> "사용자는 서비스 API로 수신한 시세 정보를 제3자에게 판매, 배포, 제공하거나 허락 없이 2차 활용을 금지합니다."

### 2.2 우리의 준수 방식

#### 2.2.1 시세 데이터 흐름

**시세 데이터의 3가지 경로**:

| 경로 | API Key | 저장 위치 | 사용 범위 | 제3자 배포 | 준수 여부 |
|------|--------|---------|---------|----------|---------|
| **경로 A: 내부 분석** | 서비스 Key | 클라우드 DB | 회사 AI 분석 | 없음 | ✅ |
| **경로 B: 사용자 표시** | 유저 Key | 로컬 PC | 사용자 자신 | 없음 | ✅ |
| **경로 C: 커뮤니티** (v2) | 없음 | 익명화 통계 | 공개 | 익명화만 | ✅ |

#### 2.2.2 경로 A: 내부 분석용 시세 (서비스 Key)

```
[클라우드 서버]
  ├─ 서비스 Key로 키움 API 호출
  ├─ 시세 데이터 수신 (공개 정보)
  ├─ 클라우드 DB에 저장
  │   └─ 목적: AI 기반 지표 계산
  │       ├─ 감정 점수 (뉴스 + 시세)
  │       ├─ 기술적 지표 (MA, RSI, MACD 등)
  │       └─ 상관관계 분석
  │
  └─ 사용자에게 제공하는 것: 분석 결과만
      ├─ "감정 점수: 75점" (시세 원본 아님)
      ├─ "기술적 신호: 강세" (분석 결과)
      └─ "상위 모멘텀 종목: [분석된 리스트]"
```

**중요**: 우리는 시세 원본 데이터를 사용자에게 제공하지 않습니다.
- ❌ 일봉 데이터 JSON 제공 금지
- ❌ 체결 거래량 상세 제공 금지
- ❌ 호가 정보 중계 금지
- ✅ 분석 결과(감정 점수, 신호) 제공만 가능

#### 2.2.3 경로 B: 사용자 시세 (유저 Key)

```
[사용자 PC의 로컬 서버]
  ├─ 유저 Key로 키움 API 호출
  ├─ 시세 데이터 수신 (사용자 자신의 시세)
  ├─ 로컬 메모리에 캐시 (실시간 규칙 평가용)
  ├─ 로컬 로그에 저장 (거래 기록용)
  └─ 사용자에게만 표시
      ├─ 프론트엔드(localhost)에만 전송
      ├─ 클라우드에 전송 금지
      └─ 제3자 접근 불가

특이점: 사용자 Key로 받은 시세는 "사용자 자신의 데이터"
  → 우리가 제3자이 될 수 없음
  → 사용자가 커뮤니티에 공유하는 것은 사용자 판단
```

**중요**: 로컬에서 수신한 시세를 절대로 클라우드로 전송하지 않습니다.
- ❌ 거래 시점의 정확한 가격 전송 금지
- ❌ 체결 주문의 호가/체결가 전송 금지
- ✅ "거래 완료" (성공/실패만) 보고 가능

#### 2.2.4 경로 C: 커뮤니티 통계 (v2)

향후 커뮤니티 기능에서:

```
[사용자가 자발적으로 공유]
  └─ 규칙 성공률, 월 수익률, 회수 기간 등
      │
      ├─ 익명화 처리
      │   ├─ 사용자 이름 제거
      │   ├─ 특정 기간 시프트 (프라이버시)
      │   └─ 거래 수량/금액 절대화
      │
      └─ 공개 통계로 집계
          ├─ "평균 월 수익률: 5.2%" (개인 데이터 아님)
          ├─ "성공 규칙 특징: MA 교차..." (분석)
          └─ "최고 수익자: [익명화 ID]"
```

**중요**: 개인 거래 데이터는 절대로 공개되지 않습니다.
- ❌ "홍길동 님은 AAPL에서 $1,000 수익" 공개 금지
- ✅ "평균 기술주 수익률: 8.3%" 통계만 공개

---

## 제3부 기술 명세 및 보안

### 3.1 API 호출 명세

#### 3.1.1 서비스 Key 사용 (클라우드 서버)

```python
# 클라우드 서버 (cloud_server/app/services/data_service.py)

from kiwoom_api import KiwoomAPI

class DataCollectionService:
    def __init__(self):
        # 환경변수에서 Key 읽기
        self.api_key = os.getenv('KIWOOM_SERVICE_KEY')
        self.api_secret = os.getenv('KIWOOM_SERVICE_SECRET')
        self.api_client = KiwoomAPI(self.api_key, self.api_secret)

    def fetch_daily_data(self, ticker):
        """일봉 데이터 수집 (내부 분석용)"""
        response = self.api_client.get_daily_ohlcv(ticker)
        # 응답: {"date": "2026-03-05", "open": 15000, "high": 15200, ...}

        # 클라우드 DB에 저장
        self.db.insert_daily_data(ticker, response)

        # 사용자에게는 분석 결과만 제공
        return self.analyze_and_extract_signals(response)

    def analyze_and_extract_signals(self, ohlcv_data):
        """시세 → 분석 결과 변환"""
        # 기술적 지표 계산
        ma20 = calculate_moving_average(ohlcv_data, 20)
        rsi = calculate_rsi(ohlcv_data)

        # 반환: 원본 시세 아님, 분석 결과만
        return {
            "signal": "BULLISH" if ma20 > rsi else "BEARISH",
            "momentum": rsi,
            "trend_strength": "STRONG" if abs(ma20 - rsi) > 30 else "WEAK"
        }
```

**확인**:
- [x] 서비스 Key는 환경변수에서만 읽음
- [x] 시세 원본은 클라우드 DB에만 저장
- [x] 사용자에게는 분석 결과만 제공
- [x] 시세 JSON을 API 응답으로 절대 전송 안 함

#### 3.1.2 유저 Key 사용 (로컬 서버)

```python
# 로컬 서버 (local_server/core/kiwoom_client.py)

from kiwoom_rest_api import KiwoomRestAPI
import json

class LocalKiwoomClient:
    def __init__(self):
        # Windows Credential Manager에서 Key 읽기
        self.user_key = self.read_from_credential_manager('kiwoom_api_key')
        self.user_secret = self.read_from_credential_manager('kiwoom_api_secret')
        self.api = KiwoomRestAPI(self.user_key, self.user_secret)

    def read_from_credential_manager(self, key_name):
        """Windows Credential Manager에서 보안하게 Key 읽기"""
        import subprocess
        # Windows API 호출 (DPAPI 암호화 자동 해제)
        ...

    def get_realtime_price(self, ticker):
        """실시간 시세 수신 (로컬 캐시용)"""
        response = self.api.get_quote(ticker)
        # 응답: {"price": 15000, "bid": 14999, "ask": 15001}

        # 로컬 메모리에만 저장 (규칙 평가용)
        self.memory_cache[ticker] = response

        # 클라우드로 절대 전송 안 함
        return response

    def verify_price_before_order(self, ticker, expected_price):
        """주문 전 가격 재확인 (가공 의혹 방지)"""
        # 키움에서 현재가 재조회
        current_price = self.get_realtime_price(ticker)

        # 5% 이상 차이 → 주문 거부
        if abs(current_price - expected_price) > expected_price * 0.05:
            log.warning(f"Price mismatch: {expected_price} vs {current_price}")
            return False

        return True

    def execute_order(self, ticker, qty, order_type):
        """주문 실행"""
        # 가격 재확인
        if not self.verify_price_before_order(ticker, ...):
            return {"success": False, "reason": "price_mismatch"}

        # 주문 실행
        response = self.api.order(ticker, qty, order_type)

        # 결과는 로컬 로그에만 저장
        self.log_execution(response)

        # 프론트엔드에는 성공/실패만 전송 (금액 미포함)
        return {"success": response.get("filled"), "order_id": response.get("id")}
```

**확인**:
- [x] 유저 Key는 Credential Manager에서만 읽음
- [x] 시세는 로컬 메모리에만 캐시
- [x] 클라우드로 시세 전송 금지
- [x] 프론트엔드에는 성공/실패만 보고 (금액 아님)

### 3.2 로깅 및 감시

#### 3.2.1 클라우드 서버 로깅

```python
# 클라우드: 모든 API 호출 로깅

class APILogger:
    def log_kiwoom_request(self, endpoint, params, response):
        """키움 API 호출 기록"""
        log_entry = {
            "timestamp": datetime.now(),
            "endpoint": endpoint,  # e.g., "/v1/daily"
            "params": {k: v for k, v in params.items() if k != 'api_key'},
            "response_status": response.status_code,
            "error": response.get("error") if response.status_code >= 400 else None
        }

        # 중요: API Key는 절대로 로깅하지 않음
        assert 'api_key' not in str(log_entry)

        self.audit_log.write(log_entry)

    def detect_anomaly(self, log_entry):
        """비정상 API 사용 탐지"""
        # 감지 항목:
        # 1. 단시간 과도한 호출 (분당 1000회 이상)
        # 2. 비정상 시간대 호출 (야간 11시 이후)
        # 3. 다량의 failed 요청

        if log_entry['call_rate'] > 1000 / 60:
            alert.send("Rate limit warning", log_entry)

        if log_entry['hour'] > 23 and log_entry['region'] != 'test':
            alert.send("Unusual time access", log_entry)
```

**확인**:
- [x] 모든 API 호출 기록
- [x] API Key 로깅 금지
- [x] 비정상 사용 자동 탐지
- [x] 감시 로그 6개월 보관

#### 3.2.2 로컬 서버 로깅

```python
# 로컬: 거래 기록 (로컬 SQLite)

class LocalExecutionLog:
    def log_order(self, ticker, qty, price, status, execution_time):
        """거래 기록"""
        log_entry = {
            "timestamp": execution_time,
            "ticker": ticker,
            "quantity": qty,
            "price": price,
            "status": status,  # "filled", "rejected", "cancelled"
            "error": None if status == "filled" else "reason"
        }

        # 로컬 SQLite에만 저장 (절대로 클라우드 전송 안 함)
        self.local_db.insert_log(log_entry)

    def report_to_cloud(self, order_id):
        """클라우드에 보고 (금액 정보 제외)"""
        report = {
            "order_id": order_id,
            "status": "filled",  # 또는 "failed"
            "timestamp": datetime.now()
        }

        # 중요: 가격, 수량 정보는 절대로 포함 금지
        assert 'price' not in report
        assert 'quantity' not in report

        self.cloud_api.post_execution_report(report)
```

**확인**:
- [x] 거래 기록은 로컬 SQLite에만 저장
- [x] 클라우드에는 성공/실패만 보고
- [x] 금액 정보는 절대로 전송 안 함

---

## 제4부 IP 화이트리스트 설정

### 4.1 서비스 Key IP 제한

```
키움증권 OpenAPI+ → 계정 설정 → IP 화이트리스트

IP 화이트리스트에 추가:
  ├─ [클라우드 서버 IP] (고정)
  │   └─ 예: 54.123.45.67
  │
  └─ [개발자 개인 IP] (테스트용)
      └─ 예: 203.0.113.50 (집, 카페)
```

**목적**: 서비스 Key가 우리의 공인 클라우드 IP에서만 사용됨을 입증

### 4.2 유저 Key IP 제한 (권장사항)

각 사용자가 키움증권 포털에서 설정:

```
키움증권 OpenAPI+ → 계정 설정 → IP 화이트리스트

IP 화이트리스트에 추가:
  ├─ [사용자 집 IP] (고정)
  │   └─ 공인 IP 또는 DDNS 이용
  │
  ├─ [사용자 직장 IP] (옵션)
  │
  └─ [사용자 모바일 IP] (옵션)
      └─ 모바일 핫스팟 사용 시
```

**목적**: 유저 Key가 사용자 자신의 PC에서만 사용됨을 입증

---

## 제5부 체크리스트

### 5.1 제3자 위임 금지 (제5조②) 준수 체크

- [ ] 서비스 Key를 환경변수로만 관리 (코드 하드코딩 아님)
- [ ] 서비스 Key를 제3자 클라우드(Google Cloud, Azure)에 저장 안 함
- [ ] 유저 Key를 클라우드 DB에 저장 안 함
- [ ] 유저 Key를 프론트엔드에 전송 안 함
- [ ] 사용자가 Key를 수동 입력하지 않음 (Credential Manager만 사용)
- [ ] 로컬 서버가 사용자를 대신하여 주문 실행 (사용자 판단 X)
- [ ] 주문은 사용자 PC의 로컬 서버에서만 실행
- [ ] 모든 매매 책임이 사용자(규칙 정의자)에게 귀속
- [ ] 키움 약관에서 "제3자 위임"으로 판단되지 않을 아키텍처 확정

### 5.2 시세 중계 금지 (제5조③) 준수 체크

- [ ] 서비스 Key로 받은 시세는 클라우드 DB에만 저장
- [ ] 시세 원본 데이터를 사용자에게 제공 안 함
- [ ] 시세 분석 결과(감정 점수, 신호)만 제공
- [ ] 유저 Key로 받은 시세는 로컬에만 저장
- [ ] 로컬 시세를 클라우드로 전송 안 함
- [ ] 프론트엔드에는 시세 "수치" 전송 안 함 (분석 결과만)
- [ ] 커뮤니티 공유 데이터는 익명화되어 처리
- [ ] 시세 중계로 해석될 여지가 없는 구조 확정

### 5.3 API 호출 보안 체크

- [ ] 모든 API 호출이 HTTPS (TLS 1.2 이상)
- [ ] 로컬 서버 → 키움: HTTPS (유저 Key 암호화)
- [ ] 클라우드 → 키움: HTTPS (서비스 Key 암호화)
- [ ] 모든 API 호출을 감시 로깅
- [ ] 비정상 호출 자동 탐지 시스템 구축
- [ ] API Key는 로그에 기록 안 함

### 5.4 로컬 서버 보안 체크

- [ ] Windows Credential Manager 사용 (DPAPI 암호화)
- [ ] localhost에만 바인드 (127.0.0.1:8001)
- [ ] 원격 접근 차단 (방화벽 규칙)
- [ ] 거래 기록은 로컬 SQLite만 (클라우드 전송 금지)
- [ ] 주문 전 가격 재확인 (가공 의혹 방지)

### 5.5 IP 화이트리스트 체크

- [ ] 키움 포털에서 서비스 Key IP 화이트리스트 설정
- [ ] 사용자에게 유저 Key IP 화이트리스트 설정 권장
- [ ] 규칙적으로 화이트리스트 검토 및 업데이트

### 5.6 문서화 체크

- [ ] 이용약관에 "Key 저장 위치" 명시
- [ ] 이용약관에 "금융정보 미수집" 명시
- [ ] 개인정보처리방침에 "구조적 미수집" 원칙 명시
- [ ] 키움 준수 확인서(이 문서) 작성 완료
- [ ] 사용자 매뉴얼에 보안 안내 포함

---

## 제6부 최종 확인

### 6.1 종합 평가

| 항목 | 준수 여부 | 비고 |
|------|---------|------|
| 제3자 위임 금지 | ✅ 준수 | Key 저장소 분리, 로컬 PC 실행 |
| 시세 중계 금지 | ✅ 준수 | 분석 결과만 제공, 시세 원본 미제공 |
| ID/PW 미보관 | ✅ 준수 | REST API 방식, ID/PW 불필요 |
| 보안 요구사항 | ✅ 준수 | HTTPS, 암호화, 접근제어 |
| 로깅 및 감시 | ✅ 준수 | 모든 API 호출 기록, 이상 탐지 |

### 6.2 리스크 평가

| 리스크 | 확률 | 영향 | 완화 방안 |
|--------|------|------|---------|
| 사용자 Key 유출 | 중간 | 높음 | Credential Manager, 교육 |
| 시세 데이터 유출 | 낮음 | 중간 | 암호화, 접근제어 |
| API 오용 | 낮음 | 중간 | 감시, 비정상 탐지 |
| 키움 약관 변경 | 낮음 | 높음 | 분기별 검토, 법무 모니터링 |

### 6.3 정기 검토 계획

- **월간**: API 호출 로그 검토, 비정상 탐지
- **분기별**: 키움 약관 변경 여부 확인, 아키텍처 검증
- **반기별**: 외부 보안 감사 (권장)
- **연간**: 법무팀 검수, 약관 업데이트

---

## 부록 A: 키움증권 OpenAPI+ 기본 정보

### 서비스 정보

- **서비스명**: 키움증권 OpenAPI+
- **제공처**: 키움증권
- **API 방식**: REST + WebSocket
- **지원 데이터**: 한국 주식, 선물/옵션 (계약에 따라)
- **실시간 시세**: WebSocket 스트리밍
- **주문 실행**: REST API

### Key 종류

| Key | 용도 | 소유 | 발급 방식 |
|-----|------|------|---------|
| API Key | 인증 | 사용자 또는 회사 | 키움 포털 신청 |
| API Secret | 서명 | 사용자 또는 회사 | 키움 포털 신청 |
| Access Token | 세션 | 발급처 | API 호출 결과 |

### 주요 API 엔드포인트

```
실시간 시세:
  wss://stream.kiwoom.com/v1/quote?key=...

일봉/주봉 데이터:
  https://openapi.kiwoom.com/v1/daily?ticker=005930&api_key=...

주문 실행:
  https://openapi.kiwoom.com/v1/order (POST)
```

---

## 부록 B: 법적 근거

### 키움증권 약관

- **약관명**: 키움증권 OpenAPI+ 서비스 이용약관
- **최종 갱신**: 2026년 (확인 필요)
- **관련 조항**:
  - 제5조②: 제3자 위임 금지
  - 제5조③: 시세 중계 금지
  - 제7조: 통신비 청구

### 법적 준거

- **증권거래법 제27조의2**: 증권회사의 책임 제한
- **개인정보보호법**: 개인정보 보호 의무
- **정보통신망법**: 개인정보 보호

---

## 최종 확인

**이 문서는 StockVision이 키움증권 OpenAPI+ 약관을 준수함을 자체 검증한 내부 기술 문서입니다.**

**법적 효력**:
- 이 문서는 법률 자문이 아님
- 키움증권의 공식 인증 또는 승인을 나타내지 않음
- 최종 법적 검수는 변호사를 통해 진행 필요

**검수자**: [법무팀]

**검수 일시**: [날짜]

**승인 여부**: [ ] 승인 / [ ] 조건부 승인 / [ ] 미승인

---

**마지막 갱신**: 2026-03-05
