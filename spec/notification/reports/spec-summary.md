# Notification 명세서 작성 완료 보고서

**작성일**: 2026-03-04
**상태**: 명세서 완성
**파일 위치**: `spec/notification/spec.md`

---

## 작성 내용 요약

### 1. 알림 이벤트 (10가지)

#### 거래 관련 (3가지)
- **BUY_EXECUTED**: 매수 체결 (종목명, 수량, 가격, 수수료)
- **SELL_EXECUTED**: 매도 체결 (손익, 세금 포함)
- **SIGNAL_TRIGGERED**: 조건 충족 (수동 확인 필요)

#### 시스템 관련 (3가지)
- **BRIDGE_DISCONNECTED**: 로컬 브릿지 끊김 (🔴 CRITICAL)
- **API_ERROR**: API 호출 실패 (타임아웃, 호출 제한)
- **ORDER_FAILED**: 주문 거절 (잔고 부족 등)

#### 분석/전략 (3가지)
- **BACKTEST_COMPLETED**: 백테스팅 완료 (수익률, 샤프비율)
- **AUTOTRADE_STATUS_CHANGED**: 자동매매 활성화/비활성화
- **SCORING_UPDATED**: 스코어링 업데이트 (선택사항)

#### 요약 (1가지)
- **DAILY_SUMMARY**: 일일 거래 요약 (16:00~17:00 발송)

---

### 2. 알림 채널 선택

#### Phase 2 (지금) - MVP 채널
| 채널 | 상태 | 이유 |
|------|------|------|
| **인앱 알림** | ✅ 구현 | 사용자가 플랫폼 사용 중 즉시 노출 |
| **이메일** | ✅ 구현 | 오프라인 사용자 전달, 기록성 |

#### Phase 3 - 확장
- Web Push (사용자 권한 요청, 브라우저 설정)

#### Phase 4+ - 통합
- 카카오톡, 슬랙 (타사 API)

---

### 3. 사용자 설정 (NotificationPreference)

사용자가 제어 가능:

#### 채널별 활성화
- 인앱 알림 (기본 활성화)
- 이메일 알림 (기본 활성화)
- Web Push (기본 비활성화)
- 카카오톡 (미구현)

#### 이벤트별 필터링
- 거래, 시스템, 분석, 요약 각 카테고리별 토글

#### 이메일 빈도 선택
- **실시간**: 거래 체결, 긴급 알림
- **일일 요약**: 1회/일 (17:00)
- **주간 요약**: 1회/주 (금 17:00)

---

### 4. 기술 구현 (백엔드)

#### 데이터베이스 모델
```python
# NotificationPreference (사용자 알림 설정)
- user_id (FK)
- 채널 활성화 플래그 (4개)
- 이메일 주소 및 빈도
- 이벤트별 필터 플래그 (10개)

# Notification (발송된 알림 기록)
- user_id (FK)
- event_type, title, message
- channel (email | in_app | web_push)
- metadata (JSON: 종목명, 가격, 링크 등)
- status (pending | sent | failed | read)
- created_at, sent_at, read_at
```

#### 서비스 계층 (NotificationService)
```python
async def send_notification(
    user_id, event_type, title, message,
    channels=["in_app", "email"],
    metadata=None
)
```

**주요 기능**:
1. 사용자 선호도 조회
2. 이벤트 필터링 확인
3. 채널별 비동기 발송 (이메일)
4. 인앱 알림 저장
5. 발송 기록 DB 저장

#### SMTP 이메일
- HTML 템플릿 기반
- 비동기 발송 (aiosmtplib)
- 재시도 로직 (최대 3회)

#### API 엔드포인트
```
GET    /api/v1/notifications/preferences       # 설정 조회
PATCH  /api/v1/notifications/preferences       # 설정 업데이트
GET    /api/v1/notifications/history           # 알림 기록 조회
POST   /api/v1/notifications/mark-as-read/{id} # 읽음 표시
```

---

### 5. 프론트엔드 구현

#### 타입 정의
```typescript
NotificationPreference   # 사용자 설정 객체
NotificationItem        # 알림 항목 (기록)
```

#### 서비스 계층 (notificationService)
```typescript
getPreferences()
updatePreferences(prefs)
getHistory(skip, limit)
markAsRead(id)
```

#### 컴포넌트
1. **NotificationSettingsPage**
   - 채널 토글
   - 이메일 설정
   - 이벤트 필터 (4개 카테고리, 10개 항목)

2. **NotificationCenter**
   - 알림 기록 목록
   - 읽음/읽지 않음 구분
   - 타임스탬프 표시

---

### 6. 환경 설정

```bash
# .env 추가 필요
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

### 7. 비기능 요구사항

| 항목 | 목표 |
|------|------|
| **알림 발송** | <500ms (이메일 제외, 비동기) |
| **조회 응답** | <200ms |
| **대량 발송** | 100건/초 |
| **재시도** | 최대 3회 (1시간 간격) |
| **중복 방지** | 1분 이내 중복 발송 금지 |

---

### 8. 구현 로드맵

#### Phase 2 (현재)
- [ ] NotificationService 구현
- [ ] API 엔드포인트 구현
- [ ] 프론트엔드 설정 페이지
- [ ] 거래/백테스팅 서비스와 통합

#### Phase 3
- [ ] Web Push 구현
- [ ] 알림 센터 개선

#### Phase 4+
- [ ] 카카오톡 연동
- [ ] 슬랙 연동

---

## 기존 코드와의 통합 포인트

### 1. 거래 서비스 (trading_service.py)
```python
# execute_buy_order() 체결 후
await notification_service.send_notification(
    user_id=account.user_id,
    event_type="BUY_EXECUTED",
    title=f"{symbol} 매수 완료",
    message=f"{qty}주 @ {price:,.0f}원",
    channels=["in_app", "email"],
    metadata={"symbol": symbol, "qty": qty, "price": price}
)
```

### 2. 백테스팅 서비스 (backtest_service.py)
```python
# 백테스팅 완료 후
await notification_service.send_notification(
    user_id=user_id,
    event_type="BACKTEST_COMPLETED",
    title="백테스팅 완료",
    message=f"총 수익률: {return_rate:.1f}%"
)
```

### 3. 브릿지 모니터 (bridge_monitor.py)
```python
# 연결 끊김 감지
await notification_service.send_notification(
    user_id=user_id,
    event_type="BRIDGE_DISCONNECTED",
    title="[긴급] 로컬 브릿지 연결 끊김!",
    message="마지막 정상: 09:45:30\n현재: 오프라인 (15분 경과)"
)
```

---

## 핵심 설계 원칙

1. **정보 과부하 방지**: 사용자가 관심 있는 이벤트만 알림
2. **채널 선택권**: 인앱, 이메일, Web Push 등 선택 가능
3. **기록 보존**: 모든 알림을 DB에 저장 (감사 추적)
4. **비동기 처리**: 이메일은 백그라운드에서 발송
5. **표준 응답**: 기존 `{ success, data, count }` 형식 준수

---

## 다음 단계

1. **코드 리뷰**: 명세서 검토 후 의견 수렴
2. **구현 시작**: Phase 2 NotificationService 구현
3. **통합 테스트**: 거래/백테스팅 서비스와 연동 테스트
4. **프론트엔드 개발**: 설정 페이지 및 알림 센터 UI 구현

---

**작성자**: Claude (Haiku 4.5)
**검토 예정**: Phase 2 구현 전
