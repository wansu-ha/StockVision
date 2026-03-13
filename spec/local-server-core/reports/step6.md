# Step 6 보고서: 클라우드 서버 통신 클라이언트

## 생성/수정된 파일

- `local_server/cloud/__init__.py` — 패키지 초기화
- `local_server/cloud/client.py` — httpx 기반 CloudClient
- `local_server/cloud/heartbeat.py` — 하트비트 전송 루프

## 구현 내용 요약

### client.py (CloudClient)
- httpx.AsyncClient 사용 (비동기)
- _get(), _post(): 타임아웃/HTTP오류/요청오류를 CloudClientError로 통일
- fetch_rules(): GET /api/rules → list[dict] 반환, 응답 형식 { data: [...] } 파싱
- send_heartbeat(): POST /api/local/heartbeat
- health_check(): GET /health → bool 반환

### heartbeat.py (start_heartbeat)
- asyncio 코루틴, CancelledError 로 종료
- 전송 실패 시 경고 로그 후 계속 실행 (네트워크 일시 단절 허용)
- _build_heartbeat_payload(): 현재 상태(strategy_engine running/stopped) 포함
- cloud_url 없으면 즉시 반환

## 리뷰 발견 사항

- CloudClient는 요청마다 새 AsyncClient 생성 (연결 풀 미사용)
  - 이유: 하트비트 간격(30s)이 길어 persistent connection 이점이 없음
  - 고빈도 요청이 생기면 클래스에 AsyncClient 유지하는 방식으로 변경
- fetch_rules()에서 응답이 list인 경우도 처리 (클라우드 서버 구현 전 대비)

## 테스트 결과

- 문법 검증: 정상
- 클라우드 클라이언트 테스트는 test_cloud_client.py에서 httpx MockTransport 사용
