# Step 2 보고서: 저장소 레이어

## 생성/수정된 파일

- `local_server/storage/__init__.py` — 패키지 초기화
- `local_server/storage/credential.py` — keyring 래퍼
- `local_server/storage/rules_cache.py` — JSON 규칙 캐시
- `local_server/storage/config_store.py` — config.json 관리 헬퍼
- `local_server/storage/log_db.py` — SQLite 로그 저장소

## 구현 내용 요약

### credential.py
- Windows Keyring 사용, 서비스명 `stockvision-local-server`
- 함수: save/load/delete/has credential, save/load API keys, save/load access token, clear_all
- CredentialError 예외로 keyring 실패 처리

### rules_cache.py
- `~/.stockvision/rules.json`에 저장
- sync(): 전량 교체 방식 (클라우드 동기화)
- get_rules(): 현재 캐시 반환
- 전역 싱글턴 get_rules_cache()

### config_store.py
- read_config(): 민감 정보(app_key, app_secret) 마스킹 후 반환
- update_config(): app_key/app_secret은 keyring으로 분리 저장
- Config 클래스(config.py) 위임

### log_db.py
- `~/.stockvision/logs.db` SQLite
- 테이블: logs (id, ts, ts_type, symbol, message, meta)
- 인덱스: ts, log_type
- write(): 동기 쓰기, query(): 필터/페이지네이션 지원
- LOG_TYPE_FILL/ORDER/ERROR/SYSTEM/STRATEGY 상수 정의

## 리뷰 발견 사항

- credential.py: keyring.errors.PasswordDeleteError를 별도 처리 (이미 없는 경우 무시)
- config_store.py: API 요청으로 app_key가 오면 평문 노출 방지를 위해 keyring으로 분리 저장
- log_db.py: 동기 sqlite3 사용 (aiosqlite는 라우터 레벨에서 필요할 경우 추가)
- meta 필드는 JSON TEXT로 저장, 조회 시 자동 역직렬화

## 테스트 결과

- 문법 검증: 정상
- 기능 테스트는 Step 12 (test_storage.py)에서 수행
