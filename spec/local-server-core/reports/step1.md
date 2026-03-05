# Step 1 보고서: FastAPI 스켈레톤 + 프로젝트 구조

## 생성/수정된 파일

- `sv_core/__init__.py` — 공유 라이브러리 패키지
- `sv_core/broker/__init__.py` — 브로커 서브패키지
- `sv_core/broker/base.py` — BrokerAdapter ABC stub (10개 추상 메서드)
- `local_server/__init__.py` — 로컬 서버 패키지
- `local_server/config.py` — 설정 관리 (Config 클래스, 싱글턴 get_config())
- `local_server/main.py` — FastAPI 앱, lifespan 훅, 라우터 등록, CORS
- `local_server/requirements.txt` — 의존성 목록

## 구현 내용 요약

### sv_core/broker/base.py
BrokerAdapter ABC에 10개 추상 메서드 정의:
- authenticate, is_authenticated, send_order, cancel_order
- get_current_price, get_balance, get_positions
- subscribe, unsubscribe, listen

### local_server/config.py
- Config 클래스: config.json 읽기/쓰기, 점 표기법 get/set
- 중첩 딕셔너리 재귀 병합
- DEFAULT_CONFIG: server, cloud, kiwoom, cors, sleep_prevent, log_level
- 전역 싱글턴 get_config()

### local_server/main.py
- FastAPI lifespan: 수면 방지 → 트레이 → 하트비트 순서로 시작, 역순 종료
- CORSMiddleware: localhost:5173, localhost:3000 허용
- 라우터: auth, config, status, trading, rules, logs, ws (Step 3~4에서 구현)
- /health 엔드포인트
- uvicorn 직접 실행 지원

## 리뷰 발견 사항

- lifespan에서 tray/heartbeat/sleep_prevent 임포트를 try/except로 감싸 GUI 환경 없이도 동작하게 함
- BrokerAdapter.listen()은 AsyncIterator 반환 타입 (Unit 1과 계약 일치)
- config.py의 _merge는 기본값 보존 후 오버라이드 적용 (누락 키 방지)

## 테스트 결과

- Python 문법 확인: import 체계 구성 정상
- 라우터 파일들은 Step 3에서 생성되므로, 현재 main.py는 빌드 전 상태
