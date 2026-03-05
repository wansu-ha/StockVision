# Step 7 보고서: 기동/종료 생명주기

## 생성/수정된 파일

- `local_server/main.py` — lifespan 함수에 시작/종료 훅 통합 (Step 1에서 작성)

## 구현 내용 요약

### lifespan() 함수 (main.py)
asynccontextmanager 패턴으로 FastAPI lifespan 구현:

**시작 시 (순서)**
1. 수면 방지 활성화 (`sleep_prevent` 설정이 True일 때)
2. 시스템 트레이 시작 (별도 daemon 스레드)
3. 클라우드 하트비트 asyncio.Task 생성 (cloud.url 설정 시에만)

**종료 시 (역순)**
1. 하트비트 Task 취소 및 await (CancelledError 소비)
2. 시스템 트레이 종료
3. 수면 방지 해제

### 설계 결정
- try/except로 트레이 시작 실패를 non-fatal로 처리 (headless 환경 지원)
- 하트비트는 asyncio.Task로 관리 (cancel()로 명시적 종료)
- cloud.url이 비어 있으면 하트비트 미시작 (선택적 기능)

## 리뷰 발견 사항

- asyncio.CancelledError는 BaseException이므로 별도로 catch하지 않고 raise
- 트레이 start/stop은 try/except로 감싸 종료 과정에서도 서버가 정상 종료되도록 함

## 테스트 결과

- 문법 검증: 정상 (Step 1 구현 시 이미 확인)
