"""local_server.broker.factory: BrokerAdapter 팩토리

환경변수에 따라 실제 KiwoomAdapter 또는 MockAdapter를 반환한다.

환경변수:
    BROKER_TYPE: "kiwoom" | "mock" (기본: "mock")
    KIWOOM_APP_KEY: 키움 App Key
    KIWOOM_APP_SECRET: 키움 App Secret
    KIWOOM_ACCOUNT_NO: 계좌번호
    KIWOOM_IS_MOCK: "true" | "false" (모의투자 여부, 기본: "false")
"""

import logging
import os
from decimal import Decimal

from sv_core.broker.base import BrokerAdapter

logger = logging.getLogger(__name__)

# 지원하는 브로커 타입
BROKER_TYPE_KIWOOM = "kiwoom"
BROKER_TYPE_MOCK = "mock"


class AdapterFactory:
    """BrokerAdapter 생성 팩토리."""

    @staticmethod
    def create(
        broker_type: str | None = None,
        **kwargs,
    ) -> BrokerAdapter:
        """BrokerAdapter 인스턴스를 생성한다.

        Args:
            broker_type: "kiwoom" | "mock" (None이면 환경변수 BROKER_TYPE 사용)
            **kwargs: 어댑터별 추가 인자 (KiwoomAdapter의 경우 app_key, app_secret 등)

        Returns:
            BrokerAdapter: 적절한 어댑터 인스턴스

        Raises:
            ValueError: 알 수 없는 broker_type 지정 시
            EnvironmentError: 키움 어댑터에 필요한 환경변수 누락 시
        """
        resolved_type = broker_type or os.getenv("BROKER_TYPE", BROKER_TYPE_MOCK)

        if resolved_type == BROKER_TYPE_KIWOOM:
            return AdapterFactory._create_kiwoom(**kwargs)
        elif resolved_type == BROKER_TYPE_MOCK:
            return AdapterFactory._create_mock(**kwargs)
        else:
            raise ValueError(
                f"알 수 없는 broker_type: '{resolved_type}'. "
                f"지원: {BROKER_TYPE_KIWOOM}, {BROKER_TYPE_MOCK}"
            )

    @staticmethod
    def _create_kiwoom(**kwargs) -> "KiwoomAdapter":  # type: ignore[name-defined]
        """KiwoomAdapter를 생성한다."""
        from local_server.broker.kiwoom.adapter import KiwoomAdapter

        app_key = kwargs.get("app_key") or os.getenv("KIWOOM_APP_KEY")
        app_secret = kwargs.get("app_secret") or os.getenv("KIWOOM_APP_SECRET")
        account_no = kwargs.get("account_no") or os.getenv("KIWOOM_ACCOUNT_NO")
        is_mock = kwargs.get("is_mock") or (os.getenv("KIWOOM_IS_MOCK", "false").lower() == "true")

        missing = [
            name for name, val in [
                ("app_key", app_key),
                ("app_secret", app_secret),
                ("account_no", account_no),
            ]
            if not val
        ]
        if missing:
            raise EnvironmentError(
                f"KiwoomAdapter 생성에 필요한 설정 누락: {missing}. "
                "환경변수 KIWOOM_APP_KEY, KIWOOM_APP_SECRET, KIWOOM_ACCOUNT_NO를 설정하세요."
            )

        logger.info("KiwoomAdapter 생성 (is_mock=%s, account=%s...)", is_mock, account_no[:4])
        return KiwoomAdapter(
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            is_mock=is_mock,
        )

    @staticmethod
    def _create_mock(**kwargs) -> "MockAdapter":  # type: ignore[name-defined]
        """MockAdapter를 생성한다."""
        from local_server.broker.mock.adapter import MockAdapter

        initial_cash = kwargs.get("initial_cash", Decimal("10_000_000"))
        logger.info("MockAdapter 생성 (initial_cash=%s)", initial_cash)
        return MockAdapter(initial_cash=initial_cash)


def create_adapter(broker_type: str | None = None, **kwargs) -> BrokerAdapter:
    """AdapterFactory.create의 편의 함수.

    Args:
        broker_type: "kiwoom" | "mock" | None
        **kwargs: 어댑터별 인자

    Returns:
        BrokerAdapter: 어댑터 인스턴스
    """
    return AdapterFactory.create(broker_type, **kwargs)
