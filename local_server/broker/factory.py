"""local_server.broker.factory: BrokerAdapter 팩토리

환경변수에 따라 실제 KisAdapter 또는 MockAdapter를 반환한다.

환경변수:
    BROKER_TYPE: "kis" | "mock" (기본: "mock")
    KIS_APP_KEY: 한국투자증권 App Key
    KIS_APP_SECRET: 한국투자증권 App Secret
    KIS_ACCOUNT_NO: 계좌번호
    KIS_IS_MOCK: "true" | "false" (모의투자 여부, 기본: "false")
"""

import logging
import os
from decimal import Decimal

from sv_core.broker.base import BrokerAdapter

logger = logging.getLogger(__name__)

# 지원하는 브로커 타입
BROKER_TYPE_KIS = "kis"
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
            broker_type: "kis" | "mock" (None이면 환경변수 BROKER_TYPE 사용)
            **kwargs: 어댑터별 추가 인자 (KisAdapter의 경우 app_key, app_secret 등)

        Returns:
            BrokerAdapter: 적절한 어댑터 인스턴스

        Raises:
            ValueError: 알 수 없는 broker_type 지정 시
            EnvironmentError: KIS 어댑터에 필요한 환경변수 누락 시
        """
        resolved_type = broker_type or os.getenv("BROKER_TYPE", BROKER_TYPE_MOCK)

        if resolved_type == BROKER_TYPE_KIS:
            return AdapterFactory._create_kis(**kwargs)
        elif resolved_type == BROKER_TYPE_MOCK:
            return AdapterFactory._create_mock(**kwargs)
        else:
            raise ValueError(
                f"알 수 없는 broker_type: '{resolved_type}'. "
                f"지원: {BROKER_TYPE_KIS}, {BROKER_TYPE_MOCK}"
            )

    @staticmethod
    def _create_kis(**kwargs) -> "KisAdapter":  # type: ignore[name-defined]
        """KisAdapter를 생성한다."""
        from local_server.broker.kis.adapter import KisAdapter

        app_key = kwargs.get("app_key") or os.getenv("KIS_APP_KEY")
        app_secret = kwargs.get("app_secret") or os.getenv("KIS_APP_SECRET")
        account_no = kwargs.get("account_no") or os.getenv("KIS_ACCOUNT_NO")
        is_mock = kwargs.get("is_mock") or (os.getenv("KIS_IS_MOCK", "false").lower() == "true")

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
                f"KisAdapter 생성에 필요한 설정 누락: {missing}. "
                "환경변수 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO를 설정하세요."
            )

        logger.info("KisAdapter 생성 (is_mock=%s, account=%s...)", is_mock, account_no[:4])
        return KisAdapter(
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
        broker_type: "kis" | "mock" | None
        **kwargs: 어댑터별 인자

    Returns:
        BrokerAdapter: 어댑터 인스턴스
    """
    return AdapterFactory.create(broker_type, **kwargs)
