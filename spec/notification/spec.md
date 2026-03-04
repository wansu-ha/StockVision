# 알림 시스템 명세서 (notification)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 계획

## 1. 개요

StockVision은 AI 기반 주식 시스템매매 자동화 플랫폼이다.
사용자는 가상거래, 백테스팅, 자동매매 규칙 실행 중 발생하는 중요한 이벤트를 실시간으로 알아야 한다.

**알림 시스템의 목표:**
- 거래 실행 결과를 즉시 전달 (매수/매도 체결)
- 주의 필요 상황 안내 (조건 충족, 브릿지 끊김, 에러)
- 일일 거래 요약 제공
- 사용자 설정에 따라 다양한 채널로 전달

**핵심 원칙: 정보 과부하 방지, 중요도 기반 필터링, 채널 선택권 제공**

---

## 2. 알림 이벤트 정의

### 2.1 거래 관련 (우선도: 높음)

#### E-1: 매수 체결 (BUY_EXECUTED)
- **발생 조건**: 매수 주문이 성공적으로 체결됨
- **전달 정보**:
  - 종목명 (예: 삼성전자)
  - 수량
  - 체결 가격
  - 체결 시간
  - 예상 수수료
- **예시**:
  ```
  🟢 삼성전자 매수 완료
  1,000주 @ 75,000원 (2026-03-04 10:30:45)
  수수료: 1,125원
  ```

#### E-2: 매도 체결 (SELL_EXECUTED)
- **발생 조건**: 매도 주문이 성공적으로 체결됨
- **전달 정보**:
  - 종목명
  - 수량
  - 체결 가격
  - 체결 시간
  - 손익 (손실은 빨간색)
  - 예상 세금/수수료
- **예시**:
  ```
  🔴 삼성전자 매도 완료
  1,000주 @ 78,000원 (2026-03-04 15:30:00)
  손익: +3,000,000원 (+4.0%)
  세금/수수료: -75,600원
  ```

#### E-3: 조건 충족 (SIGNAL_TRIGGERED)
- **발생 조건**: 자동매매 규칙의 조건이 충족되었으나 미실행 (수동 확인 필요)
- **전달 정보**:
  - 규칙명
  - 충족된 조건
  - 종목
  - 현재 스코어
  - 권장 조치
- **예시**:
  ```
  ⚠️ "저가 매수" 규칙 조건 충족
  종목: 카카오
  현재 스코어: 85점
  조건: RSI < 30 (현재 28)
  → 매수할까요? [수동 승인 필요]
  ```

### 2.2 시스템 관련 (우선도: 높음)

#### E-4: 브릿지 연결 끊김 (BRIDGE_DISCONNECTED)
- **발생 조건**: 로컬 브릿지가 키움증권 API와 연결이 끊어짐
- **심각도**: 🔴 CRITICAL
- **전달 정보**:
  - 마지막 정상 연결 시간
  - 끊긴 지난 시간
  - 재연결 시도 횟수
  - 수동 해결 가이드
- **예시**:
  ```
  🔴 [긴급] 로컬 브릿지 연결 끊김!
  마지막 정상: 2026-03-04 09:45:30
  현재: 오프라인 (15분 경과)

  조치:
  1. 로컬 브릿지 프로세스 확인 (Ctrl+C)
  2. 네트워크 연결 확인
  3. 브릿지 재시작: python bridge.py
  ```

#### E-5: API 오류 (API_ERROR)
- **발생 조건**: 키움증권 API 호출 실패 (타임아웃, 인증 오류, 호출 제한 등)
- **심각도**: 🟠 HIGH
- **전달 정보**:
  - 오류 유형
  - 재시도 상태
  - 영향받는 기능
  - 해결 안내
- **예시**:
  ```
  🟠 API 오류: 호출 제한 도달
  09:00~10:00 요청량 초과
  다음 시도 가능: 10:05
  영향: 실시간 시세 일시 중단
  ```

#### E-6: 주문 실패 (ORDER_FAILED)
- **발생 조건**: 매수/매도 주문이 거절됨
- **심각도**: 🟠 HIGH
- **전달 정보**:
  - 주문 상세 (종목, 수량, 가격)
  - 거절 사유
  - 권장 조치
- **예시**:
  ```
  🟠 주문 실패: 매수 불가
  종목: 카카오 (1,000주 @ 50,000원)
  사유: 잔고 부족 (보유: 40,000,000원 < 필요: 50,000,000원)
  조치: 매수 수량 줄이거나 자본금 추가
  ```

### 2.3 분석/전략 관련 (우선도: 중간)

#### E-7: 백테스팅 완료 (BACKTEST_COMPLETED)
- **발생 조건**: 백테스팅 실행이 완료됨
- **전달 정보**:
  - 전략명
  - 시뮬레이션 기간
  - 최종 수익률
  - 샤프비율, 최대 낙폭
  - 거래 횟수
  - 결과 조회 링크
- **예시**:
  ```
  ✅ 백테스팅 완료: "우량주 저가 매수"
  기간: 2024-01-01 ~ 2026-03-04 (2년)
  총 수익률: +45.3%
  샤프비율: 1.82
  최대 낙폭: -12.5%
  거래 횟수: 28회
  → 상세 결과 보기
  ```

#### E-8: 자동매매 활성화/비활성화 (AUTOTRADE_STATUS_CHANGED)
- **발생 조건**: 사용자가 자동매매 규칙을 활성화/비활성화함
- **심각도**: 정보성
- **전달 정보**:
  - 규칙명
  - 상태 (활성화 / 비활성화)
  - 변경 시간
- **예시**:
  ```
  ℹ️ 자동매매 규칙 활성화됨
  규칙: "우량주 저가 매수"
  상태: 활성화 (진행 중)
  시간: 2026-03-04 09:00:00
  ```

#### E-9: 스코어링 업데이트 (SCORING_UPDATED)
- **발생 조건**: 매일 또는 정기적으로 스코어링이 업데이트됨 (선택사항)
- **심각도**: 정보성
- **전달 정보**:
  - 상위 3개 종목 (스코어 기준)
  - 변동 현황 (↑ ↓)
  - 스코어 분포
- **예시**:
  ```
  📊 오늘의 스코어 TOP 3
  1. 삼성전자 (92점) ↑
  2. SK하이닉스 (88점) ↓
  3. NAVER (85점) →
  → 전체 스코어 보기
  ```

### 2.4 일일 요약 (우선도: 낮음)

#### E-10: 일일 거래 요약 (DAILY_SUMMARY)
- **발생 조건**: 매일 장 마감 후 (16:00~17:00)
- **전달 정보**:
  - 오늘 거래 건수
  - 매수/매도 금액
  - 일일 손익
  - 보유 포지션 수
  - 계좌 잔고 변동률
- **예시**:
  ```
  📈 2026-03-04 거래 요약
  거래 건수: 5회 (매수 3, 매도 2)
  매수: 15,000,000원 / 매도: 18,000,000원
  일일 손익: +2,800,000원 (+1.5%)
  보유 포지션: 4개
  계좌 현황: 102,800,000원 (+2.8%)
  ```

---

## 3. 알림 채널 비교 및 선택

### 3.1 채널별 특성 비교

| 채널 | 우선 사항 | 지연 시간 | 풍부성 | 사용자 습관 | Phase | 구현 복잡도 |
|------|---------|---------|--------|----------|-------|----------|
| **인앱 알림** | 정보성, 인터렉션 | <1초 | ⭐⭐⭐⭐⭐ 높음 | UI 화면 시 노출 | 2 | ⭐⭐ 낮음 |
| **이메일** | 중요도 높음, 기록성 | 1~5분 | ⭐⭐⭐⭐ 중간 | 비정기 확인 | 2 | ⭐⭐ 낮음 |
| **Web Push** | 긴급성, 즉시성 | <10초 | ⭐⭐⭐ 중간 | 데스크톱 활용 시 | 3 | ⭐⭐⭐ 중간 |
| **카카오톡** | 접근성, 인지도 | 1~2초 | ⭐⭐⭐⭐ 중간 | 국내 최고 사용률 | 4 | ⭐⭐⭐⭐ 높음 |
| **슬랙** | 팀 협업, 모니터링 | <2초 | ⭐⭐⭐⭐⭐ 높음 | 개발/운영팀만 | 4 | ⭐⭐⭐ 중간 |

### 3.2 Phase별 구현 전략

#### Phase 2 (MVP, 지금)
**선택**: 인앱 알림 + 이메일

**이유**:
- 인앱 알림: 사용자가 이미 플랫폼 사용 중 → 즉시 반응
- 이메일: 오프라인 사용자에게도 전달 가능, 기록성 좋음
- 복잡도 낮음, 타사 API 불필요

**미구현 채널**:
- Web Push: 사용자 권한 요청, 브라우저 설정 필요 (Phase 3 보조)
- 카카오톡/슬랙: 타사 API, 비용 (Phase 4+)

#### Phase 3 (확장)
추가: Web Push 알림

#### Phase 4+ (통합)
추가: 카카오톡, 슬랙

---

## 4. 사용자 설정 (알림 온/오프)

### 4.1 알림 선호도 설정 페이지

사용자가 다음을 제어할 수 있음:

#### 4.1.1 채널별 활성화

```
┌─ 알림 채널 설정 ────────────────────┐
│ ☑ 인앱 알림 (항상 켜짐)             │
│ ☑ 이메일 알림                       │
│ ☐ Web Push 알림                     │
│ ☐ 카카오톡 알림 (연동 필요)         │
└────────────────────────────────────┘
```

#### 4.1.2 이벤트별 필터링

```
┌─ 이벤트별 알림 설정 ──────────────────┐
│ 거래 관련                             │
│  ☑ 매수 체결                          │
│  ☑ 매도 체결                          │
│  ☑ 조건 충족 (수동 확인 필요)         │
│                                      │
│ 시스템 관련                           │
│  ☑ 브릿지 연결 끊김                   │
│  ☑ API 오류                           │
│  ☑ 주문 실패                          │
│                                      │
│ 분석/전략                             │
│  ☑ 백테스팅 완료                      │
│  ☑ 자동매매 활성화/비활성화           │
│  ☐ 스코어링 업데이트 (너무 자주)      │
│                                      │
│ 요약                                 │
│  ☑ 일일 거래 요약 (16:00~17:00)      │
└────────────────────────────────────┘
```

#### 4.1.3 이메일 주소 관리

```
┌─ 이메일 설정 ──────────────────────┐
│ 이메일 주소: user@example.com      │
│ [변경] [다른 주소 추가]             │
│                                   │
│ 이메일 빈도:                      │
│ ◉ 실시간 (거래 체결, 긴급)         │
│ ◯ 일일 요약 (1회/일, 17:00)       │
│ ◯ 주간 요약 (1회/주, 금 17:00)   │
└───────────────────────────────────┘
```

### 4.2 데이터베이스 모델

```python
# backend/app/models/notification.py

class NotificationPreference(Base):
    """사용자 알림 선호도"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 채널별 활성화
    email_enabled = Column(Boolean, default=True)
    web_push_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)
    kakao_enabled = Column(Boolean, default=False)

    # 이메일 주소
    email = Column(String(255), nullable=False)

    # 이메일 빈도
    email_frequency = Column(
        String(20),
        default="realtime"  # realtime | daily | weekly
    )

    # 이벤트 필터링
    notify_buy_executed = Column(Boolean, default=True)
    notify_sell_executed = Column(Boolean, default=True)
    notify_signal_triggered = Column(Boolean, default=True)
    notify_bridge_disconnected = Column(Boolean, default=True)
    notify_api_error = Column(Boolean, default=True)
    notify_order_failed = Column(Boolean, default=True)
    notify_backtest_completed = Column(Boolean, default=True)
    notify_autotrade_status_changed = Column(Boolean, default=False)
    notify_scoring_updated = Column(Boolean, default=False)
    notify_daily_summary = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Notification(Base):
    """발송된 알림 기록"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    event_type = Column(String(50), nullable=False)  # BUY_EXECUTED, BRIDGE_DISCONNECTED, etc.

    # 알림 내용
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), nullable=False)  # email | in_app | web_push | kakao

    # 메타데이터 (JSON)
    metadata = Column(JSON, nullable=True)  # 종목명, 가격, 링크 등

    # 상태
    status = Column(String(20), default="pending")  # pending | sent | failed | read
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
```

---

## 5. 기술 요구사항

### 5.1 백엔드 구현

#### 의존성 추가

```
# requirements.txt
python-dotenv==1.0.0          # 환경 변수
jinja2==3.1.2                 # 이메일 템플릿
aiosmtplib==2.1.1             # 비동기 이메일 발송
```

#### 서비스 계층

##### NotificationService (신규)

```python
# backend/app/services/notification_service.py

from datetime import datetime
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationPreference

class NotificationService:
    """알림 발송 및 관리"""

    def __init__(self, db: Session):
        self.db = db

    async def send_notification(
        self,
        user_id: int,
        event_type: str,
        title: str,
        message: str,
        channels: list[str] = ["in_app", "email"],
        metadata: dict = None
    ) -> dict:
        """알림 생성 및 발송"""

        # 1. 사용자 선호도 확인
        pref = self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

        if not pref:
            return {"success": False, "error": "알림 설정이 없습니다"}

        # 2. 이벤트별 필터링 확인
        if not self._should_notify(event_type, pref):
            return {"success": True, "skipped": True, "reason": "사용자 설정에 의해 필터링됨"}

        # 3. 각 채널별 발송
        results = {}
        for channel in channels:
            if channel == "email" and pref.email_enabled:
                results["email"] = await self._send_email(pref.email, title, message)
            elif channel == "in_app" and pref.in_app_enabled:
                results["in_app"] = self._send_in_app(user_id, title, message)
            elif channel == "web_push" and pref.web_push_enabled:
                results["web_push"] = await self._send_web_push(user_id, title, message)

        # 4. 기록 저장
        notification = Notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            channel=",".join(results.keys()),
            metadata=metadata,
            status="sent"
        )
        self.db.add(notification)
        self.db.commit()

        return {
            "success": True,
            "notification_id": notification.id,
            "channels": results
        }

    async def _send_email(self, to_email: str, title: str, message: str) -> dict:
        """이메일 발송"""
        try:
            # SMTP 설정
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = settings.smtp_username
            msg['To'] = to_email

            # HTML 템플릿 렌더링
            html_body = self._render_email_template(title, message)
            msg.attach(MIMEText(html_body, 'html'))

            # 비동기 발송
            async with aiosmtplib.SMTP(hostname=settings.smtp_host, port=settings.smtp_port) as smtp:
                await smtp.login(settings.smtp_username, settings.smtp_password)
                await smtp.send_message(msg)

            return {"status": "sent"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _send_in_app(self, user_id: int, title: str, message: str) -> dict:
        """인앱 알림 저장"""
        # WebSocket이나 서버 전송 이벤트(SSE)로 실시간 전달
        # 또는 DB에만 저장 후 클라이언트가 폴링
        return {"status": "stored", "user_id": user_id}

    async def _send_web_push(self, user_id: int, title: str, message: str) -> dict:
        """Web Push 발송 (Phase 3)"""
        # pywebpush 또는 유사 라이브러리 사용
        return {"status": "pending"}

    def _should_notify(self, event_type: str, pref: NotificationPreference) -> bool:
        """이벤트별 필터링"""
        filter_map = {
            "BUY_EXECUTED": pref.notify_buy_executed,
            "SELL_EXECUTED": pref.notify_sell_executed,
            "SIGNAL_TRIGGERED": pref.notify_signal_triggered,
            "BRIDGE_DISCONNECTED": pref.notify_bridge_disconnected,
            "API_ERROR": pref.notify_api_error,
            "ORDER_FAILED": pref.notify_order_failed,
            "BACKTEST_COMPLETED": pref.notify_backtest_completed,
            "AUTOTRADE_STATUS_CHANGED": pref.notify_autotrade_status_changed,
            "SCORING_UPDATED": pref.notify_scoring_updated,
            "DAILY_SUMMARY": pref.notify_daily_summary,
        }
        return filter_map.get(event_type, True)

    def _render_email_template(self, title: str, message: str) -> str:
        """이메일 HTML 템플릿"""
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1e40af; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 20px; }}
                .footer {{ background-color: #e5e7eb; padding: 10px; font-size: 12px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{title}</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                </div>
                <div class="footer">
                    <p>StockVision | <a href="https://stockvision.example.com/notifications">알림 설정</a></p>
                </div>
            </div>
        </body>
        </html>
        """
```

##### 기존 서비스와의 통합

```python
# backend/app/services/trading_service.py (기존)에서 알림 호출

from app.services.notification_service import NotificationService

async def execute_buy_order(self, account_id: int, symbol: str, qty: int, price: float):
    """매수 주문 실행"""
    # ... 기존 주문 로직 ...

    # 체결 후 알림 발송
    notification_service = NotificationService(self.db)
    await notification_service.send_notification(
        user_id=account.user_id,
        event_type="BUY_EXECUTED",
        title=f"{symbol} 매수 완료",
        message=f"{qty}주 @ {price:,.0f}원",
        channels=["in_app", "email"],
        metadata={
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

#### API 엔드포인트

```python
# backend/app/api/notifications.py (신규)

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.notification import NotificationPreference, Notification
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# 인증 디펜던시 (기존)
def get_current_user(token: str = Depends(...)) -> dict:
    # JWT 검증
    pass

@router.get("/preferences")
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알림 설정 조회"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user["id"]
    ).first()

    if not pref:
        raise HTTPException(status_code=404, detail="알림 설정이 없습니다")

    return {
        "success": True,
        "data": {
            "email": pref.email,
            "email_enabled": pref.email_enabled,
            "email_frequency": pref.email_frequency,
            "web_push_enabled": pref.web_push_enabled,
            "in_app_enabled": pref.in_app_enabled,
            "events": {
                "buy_executed": pref.notify_buy_executed,
                "sell_executed": pref.notify_sell_executed,
                "signal_triggered": pref.notify_signal_triggered,
                "bridge_disconnected": pref.notify_bridge_disconnected,
                "api_error": pref.notify_api_error,
                "order_failed": pref.notify_order_failed,
                "backtest_completed": pref.notify_backtest_completed,
                "autotrade_status_changed": pref.notify_autotrade_status_changed,
                "scoring_updated": pref.notify_scoring_updated,
                "daily_summary": pref.notify_daily_summary,
            }
        },
        "count": 0
    }

@router.patch("/preferences")
async def update_notification_preferences(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알림 설정 업데이트"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user["id"]
    ).first()

    if not pref:
        raise HTTPException(status_code=404)

    # 허용된 필드만 업데이트
    for field in ["email_enabled", "web_push_enabled", "in_app_enabled", "email_frequency"]:
        if field in request:
            setattr(pref, field, request[field])

    # 이벤트 필터링
    event_map = {
        "buy_executed": "notify_buy_executed",
        "sell_executed": "notify_sell_executed",
        # ... 나머지 매핑 ...
    }

    if "events" in request:
        for key, value in request["events"].items():
            db_field = event_map.get(key)
            if db_field:
                setattr(pref, db_field, value)

    db.commit()

    return {
        "success": True,
        "data": {"message": "알림 설정이 업데이트되었습니다"},
        "count": 0
    }

@router.get("/history")
async def get_notification_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알림 기록 조회 (최근 순)"""
    notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user["id"])\
        .order_by(Notification.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    return {
        "success": True,
        "data": [
            {
                "id": n.id,
                "event_type": n.event_type,
                "title": n.title,
                "message": n.message,
                "channel": n.channel,
                "status": n.status,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None
            }
            for n in notifications
        ],
        "count": len(notifications)
    }

@router.post("/mark-as-read/{notification_id}")
async def mark_notification_as_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림을 읽음으로 표시"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user["id"]
    ).first()

    if not notification:
        raise HTTPException(status_code=404)

    notification.read_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "data": {"message": "알림이 읽음으로 표시되었습니다"},
        "count": 0
    }
```

#### main.py 수정

```python
# backend/app/main.py에 추가

from app.api import notifications

app.include_router(notifications.router)
```

### 5.2 환경 변수

```bash
# .env에 추가
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Web Push 설정 (Phase 3)
WEB_PUSH_VAPID_PUBLIC_KEY=
WEB_PUSH_VAPID_PRIVATE_KEY=
```

### 5.3 프론트엔드 구현

#### 타입 정의

```typescript
// frontend/src/types/notification.ts

export interface NotificationPreference {
  email: string;
  email_enabled: boolean;
  email_frequency: "realtime" | "daily" | "weekly";
  web_push_enabled: boolean;
  in_app_enabled: boolean;
  events: {
    buy_executed: boolean;
    sell_executed: boolean;
    signal_triggered: boolean;
    bridge_disconnected: boolean;
    api_error: boolean;
    order_failed: boolean;
    backtest_completed: boolean;
    autotrade_status_changed: boolean;
    scoring_updated: boolean;
    daily_summary: boolean;
  };
}

export interface NotificationItem {
  id: number;
  event_type: string;
  title: string;
  message: string;
  channel: string;
  status: "pending" | "sent" | "failed" | "read";
  created_at: string;
  read_at: string | null;
}
```

#### 서비스 계층

```typescript
// frontend/src/services/notificationService.ts

import axios from "axios";
import {
  NotificationPreference,
  NotificationItem,
} from "../types/notification";

class NotificationService {
  private baseUrl = "http://localhost:8000/api/v1/notifications";
  private token = localStorage.getItem("token");

  async getPreferences(): Promise<NotificationPreference> {
    const response = await axios.get(`${this.baseUrl}/preferences`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    return response.data.data;
  }

  async updatePreferences(
    preferences: Partial<NotificationPreference>
  ): Promise<void> {
    await axios.patch(`${this.baseUrl}/preferences`, preferences, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
  }

  async getHistory(skip = 0, limit = 20): Promise<NotificationItem[]> {
    const response = await axios.get(`${this.baseUrl}/history`, {
      params: { skip, limit },
      headers: { Authorization: `Bearer ${this.token}` },
    });
    return response.data.data;
  }

  async markAsRead(notificationId: number): Promise<void> {
    await axios.post(
      `${this.baseUrl}/mark-as-read/${notificationId}`,
      {},
      {
        headers: { Authorization: `Bearer ${this.token}` },
      }
    );
  }
}

export default new NotificationService();
```

#### 컴포넌트

##### NotificationSettingsPage

```typescript
// frontend/src/pages/NotificationSettings.tsx

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import notificationService from "../services/notificationService";
import { NotificationPreference } from "../types/notification";

export default function NotificationSettings() {
  const { data: preferences, isLoading } = useQuery({
    queryKey: ["notificationPreferences"],
    queryFn: () => notificationService.getPreferences(),
  });

  const updateMutation = useMutation({
    mutationFn: (prefs: Partial<NotificationPreference>) =>
      notificationService.updatePreferences(prefs),
  });

  const handleChannelToggle = (channel: string) => {
    const key = `${channel}_enabled` as keyof NotificationPreference;
    updateMutation.mutate({
      [key]: !preferences?.[key],
    } as any);
  };

  const handleEventToggle = (eventKey: string) => {
    updateMutation.mutate({
      events: {
        ...preferences?.events,
        [eventKey]: !preferences?.events[eventKey as keyof typeof preferences.events],
      },
    } as any);
  };

  if (isLoading) return <div>로딩 중...</div>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">알림 설정</h1>

      {/* 채널 설정 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">알림 채널</h2>
        <div className="space-y-4">
          {[
            { id: "in_app", label: "인앱 알림" },
            { id: "email", label: "이메일 알림" },
            { id: "web_push", label: "Web Push 알림" },
          ].map((channel) => (
            <label key={channel.id} className="flex items-center">
              <input
                type="checkbox"
                checked={preferences?.[`${channel.id}_enabled` as any] || false}
                onChange={() => handleChannelToggle(channel.id)}
                className="w-5 h-5 mr-3"
              />
              {channel.label}
            </label>
          ))}
        </div>
      </section>

      {/* 이메일 설정 */}
      {preferences?.email_enabled && (
        <section className="mb-8 p-4 bg-blue-50 rounded">
          <h3 className="font-semibold mb-3">이메일 설정</h3>
          <div className="mb-4">
            <label className="block text-sm mb-2">이메일 주소</label>
            <input
              type="email"
              value={preferences?.email || ""}
              className="w-full px-3 py-2 border rounded"
              disabled
            />
          </div>
          <div>
            <label className="block text-sm mb-2">이메일 빈도</label>
            <select
              value={preferences?.email_frequency || "realtime"}
              onChange={(e) =>
                updateMutation.mutate({
                  email_frequency: e.target.value as any,
                } as any)
              }
              className="w-full px-3 py-2 border rounded"
            >
              <option value="realtime">실시간</option>
              <option value="daily">일일 요약</option>
              <option value="weekly">주간 요약</option>
            </select>
          </div>
        </section>
      )}

      {/* 이벤트 필터링 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">알림할 이벤트</h2>

        <div className="space-y-6">
          {/* 거래 관련 */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">거래 관련</h3>
            <div className="space-y-2 ml-2">
              {[
                { key: "buy_executed", label: "매수 체결" },
                { key: "sell_executed", label: "매도 체결" },
                { key: "signal_triggered", label: "조건 충족" },
              ].map((event) => (
                <label key={event.key} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={
                      preferences?.events[event.key as keyof typeof preferences.events] || false
                    }
                    onChange={() => handleEventToggle(event.key)}
                    className="w-4 h-4 mr-2"
                  />
                  {event.label}
                </label>
              ))}
            </div>
          </div>

          {/* 시스템 관련 */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">시스템 관련</h3>
            <div className="space-y-2 ml-2">
              {[
                { key: "bridge_disconnected", label: "브릿지 연결 끊김" },
                { key: "api_error", label: "API 오류" },
                { key: "order_failed", label: "주문 실패" },
              ].map((event) => (
                <label key={event.key} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={
                      preferences?.events[event.key as keyof typeof preferences.events] || false
                    }
                    onChange={() => handleEventToggle(event.key)}
                    className="w-4 h-4 mr-2"
                  />
                  {event.label}
                </label>
              ))}
            </div>
          </div>

          {/* 분석/전략 */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">분석/전략</h3>
            <div className="space-y-2 ml-2">
              {[
                { key: "backtest_completed", label: "백테스팅 완료" },
                { key: "autotrade_status_changed", label: "자동매매 활성화/비활성화" },
                { key: "scoring_updated", label: "스코어링 업데이트" },
              ].map((event) => (
                <label key={event.key} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={
                      preferences?.events[event.key as keyof typeof preferences.events] || false
                    }
                    onChange={() => handleEventToggle(event.key)}
                    className="w-4 h-4 mr-2"
                  />
                  {event.label}
                </label>
              ))}
            </div>
          </div>

          {/* 요약 */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">요약</h3>
            <div className="space-y-2 ml-2">
              {[{ key: "daily_summary", label: "일일 거래 요약" }].map((event) => (
                <label key={event.key} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={
                      preferences?.events[event.key as keyof typeof preferences.events] || false
                    }
                    onChange={() => handleEventToggle(event.key)}
                    className="w-4 h-4 mr-2"
                  />
                  {event.label}
                </label>
              ))}
            </div>
          </div>
        </div>
      </section>

      {updateMutation.isPending && <p>업데이트 중...</p>}
    </div>
  );
}
```

##### NotificationCenter (인앱 알림 목록)

```typescript
// frontend/src/components/NotificationCenter.tsx

import { useQuery } from "@tanstack/react-query";
import notificationService from "../services/notificationService";
import { NotificationItem } from "../types/notification";

export default function NotificationCenter() {
  const { data: notifications } = useQuery({
    queryKey: ["notificationHistory"],
    queryFn: () => notificationService.getHistory(0, 20),
  });

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">알림 센터</h2>

      {notifications && notifications.length > 0 ? (
        <div className="space-y-4">
          {notifications.map((notif: NotificationItem) => (
            <div
              key={notif.id}
              className="p-4 bg-white border rounded-lg hover:shadow-md transition"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{notif.title}</h3>
                  <p className="text-gray-600 text-sm mt-1">{notif.message}</p>
                  <div className="flex gap-2 mt-2">
                    <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                      {notif.event_type}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(notif.created_at).toLocaleString("ko-KR")}
                    </span>
                  </div>
                </div>
                {!notif.read_at && (
                  <button
                    onClick={() => notificationService.markAsRead(notif.id)}
                    className="text-blue-600 hover:underline text-sm ml-4"
                  >
                    읽음
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-center py-8">알림이 없습니다.</p>
      )}
    </div>
  );
}
```

---

## 6. 데이터베이스 마이그레이션

```sql
-- migration: add_notification_tables.sql

CREATE TABLE notification_preferences (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL UNIQUE,

    email_enabled BOOLEAN DEFAULT TRUE,
    web_push_enabled BOOLEAN DEFAULT FALSE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    kakao_enabled BOOLEAN DEFAULT FALSE,

    email VARCHAR(255) NOT NULL,
    email_frequency VARCHAR(20) DEFAULT 'realtime',

    notify_buy_executed BOOLEAN DEFAULT TRUE,
    notify_sell_executed BOOLEAN DEFAULT TRUE,
    notify_signal_triggered BOOLEAN DEFAULT TRUE,
    notify_bridge_disconnected BOOLEAN DEFAULT TRUE,
    notify_api_error BOOLEAN DEFAULT TRUE,
    notify_order_failed BOOLEAN DEFAULT TRUE,
    notify_backtest_completed BOOLEAN DEFAULT TRUE,
    notify_autotrade_status_changed BOOLEAN DEFAULT FALSE,
    notify_scoring_updated BOOLEAN DEFAULT FALSE,
    notify_daily_summary BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(20) NOT NULL,
    metadata JSON,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_event_type (event_type)
);
```

---

## 7. 비기능 요구사항

### 7.1 성능

- **알림 발송**: <500ms (이메일 제외, 비동기 처리)
- **알림 조회**: <200ms
- **대량 발송**: 100건/초 처리 가능 (배경 작업)

### 7.2 신뢰성

- **이메일 재시도**: 최대 3회 (1시간 간격)
- **알림 기록**: 영구 저장 (감사 추적)
- **중복 방지**: 같은 이벤트 1분 이내 중복 발송 금지

### 7.3 보안

- **개인정보**: 이메일만 저장, 전화번호 불필요
- **HTTPS**: 알림 설정 페이지는 반드시 HTTPS 사용
- **접근 제어**: 사용자는 자신의 알림만 조회 가능

---

## 8. 구현 단계 (Phase 2, 3)

### Phase 2 (지금)
- [x] 알림 이벤트 정의
- [x] 채널 선택 (인앱 + 이메일)
- [ ] NotificationService 구현
- [ ] API 엔드포인트 구현
- [ ] 프론트엔드 설정 페이지 구현
- [ ] 거래 서비스와 통합

### Phase 3 (다음)
- [ ] Web Push 구현
- [ ] 알림 센터 개선
- [ ] 브라우저 알림 권한 요청
- [ ] 구독 관리 UI

### Phase 4+ (미래)
- [ ] 카카오톡 연동
- [ ] 슬랙 연동
- [ ] 알림 분석/통계

---

## 9. 미결 사항

### 9.1 추후 논의 필요

- [ ] Web Push 시행 시점 및 구현 방식
- [ ] 카카오톡 연동 우선순위
- [ ] 알림 빈도 기본값 (realtime vs daily)
- [ ] 스코어링 업데이트 알림 필요도 (선택사항)
- [ ] SMS 알림 필요도 (긴급 상황)

### 9.2 기술적 고려사항

- 이메일 발송 실패 시 재시도 로직
- 알림 기록 로그 분석 및 통계
- 대량 이메일 발송 시 SMTP 레이트 제한 처리
- 알림 센터 UI/UX 개선

---

## 10. 참고: 기존 API 응답 형식 준수

모든 알림 관련 API는 기존 StockVision 표준 응답 형식을 따름:

```json
{
  "success": true,
  "data": { /* 실제 데이터 */ },
  "count": 0
}
```

---

## 11. 참고 자료

- [SMTP 설정 (Gmail)](https://support.google.com/accounts/answer/185833)
- [FastAPI 백그라운드 작업](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Web Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [React Query 상태 관리](https://tanstack.com/query/latest)
