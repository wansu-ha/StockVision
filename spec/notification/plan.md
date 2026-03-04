# 알림 시스템 구현 계획서 (notification)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 | 의존: execution-engine, local-bridge

---

## 0. 방향 결정

Phase 3 알림 채널 우선순위:

| 채널 | 우선순위 | 이유 |
|------|:-------:|------|
| WS 인앱 알림 (React) | ✅ P0 | 로컬 서버 → React 이미 WS 연결 있음 |
| Windows 시스템 트레이 알림 | ✅ P1 | exe 환경에서 자연스러운 UX |
| 이메일 (Gmail/SMTP) | 🟡 P2 | 일일 요약에 적합 |
| Telegram/Kakao | 🔵 P3 | Phase 3 이후 |

---

## 1. 구현 단계

### Step 1 — WS 인앱 알림

**목표**: 체결/오류/경고를 React 알림 패널로 표시

파일: `local_server/routers/ws.py` (기존 확장)

이미 정의된 WS 메시지 타입 활용:
```json
{ "type": "alert", "data": { "level": "info|warn|error", "message": "..." } }
{ "type": "execution_result", "data": { ... } }
```

React 알림 컴포넌트:
- 우측 상단 토스트 알림 (3초 자동 사라짐)
- 알림 센터 (종 모양 아이콘 + 미읽음 배지)

파일: `frontend/src/components/NotificationCenter.tsx`

**검증:**
- [ ] 체결 이벤트 → 토스트 알림 표시
- [ ] 알림 센터에서 이력 확인
- [ ] 미읽음 배지 카운트

### Step 2 — 시스템 트레이 알림 (Windows)

**목표**: 브라우저 없이도 중요 이벤트 전달

파일: `local_server/tray.py`

```python
import pystray
from PIL import Image

class TrayApp:
    def notify(self, title: str, message: str):
        """Windows 알림 표시"""
        self.icon.notify(title=title, message=message)
```

알림 트리거:
- 체결 완료: "삼성전자 10주 매수 체결 (₩72,500)"
- 오류: "규칙 #1 평가 오류 — 자세히 보기"
- 재로그인 필요: "StockVision 재로그인 필요"
- 키움 연결 끊김: "키움 HTS 연결이 끊어졌습니다"

**검증:**
- [ ] 체결 시 Windows 알림 팝업
- [ ] 알림 클릭 → 브라우저 열기

### Step 3 — 일일 이메일 요약 (선택)

**목표**: 장 마감 후 오늘 거래 요약 이메일 발송

파일: `local_server/cloud/email_reporter.py`

```
스케줄: 16:00 KST (장 마감 30분 후)
발송 조건: 오늘 실행 건 > 0 AND 사용자 이메일 알림 설정 ON

내용:
  제목: "[StockVision] 오늘 거래 요약 (2026-03-04)"
  내용:
    - 총 실행: 3건 / 체결: 2건 / 오류: 1건
    - 포트폴리오: ₩10,000,000 → ₩10,150,000 (+1.5%)
    - 체결 내역: [삼성전자 10주 매수 ₩72,500] ...
```

**검증:**
- [ ] 16:00 KST 발송 확인
- [ ] 이메일 알림 설정 OFF → 발송 안 함
- [ ] 체결 없는 날 → 발송 안 함

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/tray.py` | 시스템 트레이 알림 |
| `local_server/cloud/email_reporter.py` | 일일 이메일 요약 |
| `frontend/src/components/NotificationCenter.tsx` | 인앱 알림 패널 |
| `frontend/src/components/Toast.tsx` | 토스트 알림 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — React 인앱 알림 (토스트 + 알림 센터)` |
| 2 | `feat: Step 2 — Windows 트레이 알림` |
| 3 | `feat: Step 3 — 일일 이메일 요약 발송` |
