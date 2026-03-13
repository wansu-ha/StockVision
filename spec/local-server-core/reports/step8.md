# Step 8 보고서: CORS 미들웨어

## 생성/수정된 파일

- `local_server/main.py` — CORSMiddleware 설정 (Step 1에서 작성)

## 구현 내용 요약

### CORS 설정 (create_app() 함수)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # ["http://localhost:5173", "http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- 허용 출처: config.cors.origins에서 로드 (기본값: localhost:5173, localhost:3000)
- 자격증명 허용 (쿠키/Authorization 헤더)
- 메서드 전체 허용
- 헤더 전체 허용

### 보안 검토
- localhost 출처만 허용 → 외부 도메인에서의 XSS 공격으로 인한 API 접근 방지
- allow_credentials=True는 allow_origins=["*"]와 조합 불가 (FastAPI가 오류 발생시킴)
  - 명시적 출처 목록 사용으로 해결

## 리뷰 발견 사항

- 설정 파일에서 origins를 읽어 런타임에 동적 변경 가능 (서버 재시작 필요)
- localhost에 한정되므로 보안 위험 낮음

## 테스트 결과

- FastAPI CORS 문서 기준 정상 구현
- OPTIONS 프리플라이트는 CORSMiddleware가 자동 처리
