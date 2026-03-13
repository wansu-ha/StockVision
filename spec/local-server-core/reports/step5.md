# Step 5 보고서: 시스템 트레이 아이콘

## 생성/수정된 파일

- `local_server/tray/__init__.py` — 패키지 초기화
- `local_server/tray/tray_app.py` — pystray 트레이 앱

## 구현 내용 요약

### tray_app.py
- pystray, Pillow를 import 시도하고 없으면 _PYSTRAY_AVAILABLE = False로 fallback
- _create_icon_image(): PIL로 64x64 파란 원형 아이콘 생성 (외부 파일 불필요)
- 트레이 메뉴: 상태 확인 (브라우저로 /api/status 열기), 종료
- start_tray(): daemon 스레드에서 pystray.Icon.run() 실행
- stop_tray(): icon.stop() 호출
- _on_quit(): os.kill(os.getpid(), 2)로 uvicorn에 SIGINT 전달

### 설계 결정
- daemon=True 스레드: FastAPI 메인 스레드 종료 시 자동으로 종료
- pystray 미설치 환경에서도 서버가 정상 기동하도록 import 실패 처리
- 아이콘 이미지를 외부 파일 없이 생성 (PyInstaller 번들 단순화)

## 리뷰 발견 사항

- _on_quit()에서 os.kill(SIGINT)을 사용해 FastAPI lifespan 종료 훅이 정상 실행되도록 함
- pystray.Menu.SEPARATOR 지원 여부는 pystray 버전에 따라 다를 수 있으므로, 설치 버전 0.19.5 이상 요구

## 테스트 결과

- GUI 환경이 없는 CI에서는 pystray import 실패 → 정상 fallback 확인 가능
- 실제 트레이 표시는 수동 테스트 필요 (Windows 환경)
