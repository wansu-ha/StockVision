# 변경 이력

이 프로젝트의 모든 주요 변경사항이 이 파일에 문서화됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)를 기반으로 하며,
이 프로젝트는 [시맨틱 버저닝](https://semver.org/spec/v2.0.0.html)을 따릅니다.

## [미배포]

### 추가됨
- 초기 프로젝트 설정 및 문서화
- FastAPI 백엔드 인프라
- yfinance를 사용한 데이터 수집 시스템
- 기술적 지표 계산 서비스
- 주식 데이터용 RESTful API 엔드포인트
- 정규화된 스키마의 SQLite 데이터베이스

### 변경됨
- 없음

### 폐지됨
- 없음

### 제거됨
- 없음

### 수정됨
- 없음

### 보안
- 없음

---

## [0.1.0] - 2025-08-21

### 추가됨
- **프로젝트 초기화**
  - StockVision 프로젝트 구조 생성
  - Git 저장소 초기화
  - 포괄적인 .gitignore 파일 추가
  - 프로젝트 문서화 구조 생성

- **백엔드 인프라**
  - CORS 미들웨어가 포함된 FastAPI 애플리케이션 설정
  - Python 가상 환경 (Python 3.13.7)
  - 의존성 관리 (requirements.txt)
  - 프로젝트 구조: `app/{api,core,models,services,utils}`

- **데이터베이스 설계**
  - SQLite 데이터베이스 연결 (개발용)
  - 주식, 가격, 기술적 지표용 데이터베이스 모델
  - 가상 거래 시스템용 데이터베이스 모델
  - 자동 거래 및 백테스팅용 데이터베이스 모델
  - 데이터베이스 초기화 스크립트

- **데이터 수집 시스템**
  - 주식 데이터 수집을 위한 yfinance 통합
  - 주식 정보 수집 (심볼, 회사명, 섹터, 산업, 시가총액)
  - 과거 가격 데이터 수집 (OHLCV)
  - 데이터 검증 및 오류 처리
  - 중복 방지가 포함된 데이터베이스 저장

- **기술적 지표 서비스**
  - RSI (상대강도지수) 계산
  - EMA (지수이동평균) - 20일 및 50일
  - MACD (이동평균수렴확산) 계산
  - 볼린저 밴드 계산
  - Pandas 기반 효율적인 계산
  - 계산된 지표의 데이터베이스 저장

- **RESTful API 구현**
  - `GET /stocks/` - 모든 주식 목록
  - `GET /stocks/{symbol}` - 주식 상세 정보
  - `GET /stocks/{symbol}/prices` - 날짜 범위별 가격 데이터
  - `GET /stocks/{symbol}/indicators` - 기술적 지표
  - `GET /stocks/{symbol}/summary` - 최신 데이터가 포함된 주식 요약
  - 적절한 오류 처리 및 HTTP 상태 코드
  - 쿼리 매개변수 검증

- **데이터 모델**
  - 기본 정보가 포함된 Stock 모델
  - OHLCV 데이터용 StockPrice 모델
  - 계산된 지표용 TechnicalIndicator 모델
  - VirtualAccount, VirtualTrade, VirtualPosition 모델
  - AutoTradingRule 및 BacktestResult 모델
  - 성능 최적화를 위한 적절한 인덱싱

- **서비스 계층**
  - 주식 데이터 수집용 DataCollector 서비스
  - 지표 계산용 TechnicalIndicatorCalculator 서비스
  - 데이터베이스 세션 관리
  - 오류 처리 및 로깅

- **테스트 및 검증**
  - 데이터 수집 테스트 스크립트
  - 기술적 지표 계산 테스트
  - curl 명령어를 사용한 API 엔드포인트 테스트
  - 5개 주요 주식 데이터 성공적 수집

### 기술적 세부사항
- **수집된 데이터**: 5개 주식 (AAPL, MSFT, GOOGL, AMZN, TSLA)
- **가격 데이터**: 주식당 249개 일일 OHLCV 기록 (총 1,245개)
- **기술적 지표**: 주식당 2,171개 지표 (총 10,855개)
- **데이터 기간**: 2024년 8월 - 2025년 1월
- **데이터베이스**: 적절한 인덱싱이 포함된 SQLite
- **API 성능**: 적절한 오류 처리가 포함된 빠른 응답 시간

### 의존성
- FastAPI 0.116.1
- uvicorn 0.35.0
- SQLAlchemy 2.0.43
- pandas 2.3.2
- numpy 2.3.2
- yfinance 0.2.65
- python-dotenv 1.1.1

### 환경 설정
- Python 3.13.7
- pip를 사용한 가상 환경
- 환경 변수 구성 (.env.example)
- 향후 PostgreSQL 마이그레이션을 위한 Docker Compose 설정

### 다음 단계
- React 프론트엔드 개발
- 차트 시각화 구현
- 대시보드 UI/UX 설계
- PostgreSQL 마이그레이션
- ML 모델 구현

---

## [0.0.1] - 2025-08-21

### 추가됨
- 초기 프로젝트 구조
- 기본 문서화
- 개발 계획 및 아키텍처 설계
- 프로젝트 청사진 및 로드맵

---

## 버전 이력

- **0.1.0** - 백엔드 인프라 및 데이터 수집 시스템
- **0.0.1** - 프로젝트 초기화 및 계획

## 참고사항

- 모든 날짜는 YYYY-MM-DD 형식입니다
- 이 프로젝트는 시맨틱 버저닝 (MAJOR.MINOR.PATCH)을 따릅니다
- 미배포 섹션에는 다음 릴리스에 포함될 변경사항이 있습니다
- 각 버전은 명확한 릴리스 날짜와 포괄적인 변경 목록을 가져야 합니다
