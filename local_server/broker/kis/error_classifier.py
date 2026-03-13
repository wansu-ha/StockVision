"""local_server.broker.kis.error_classifier: API 에러 분류 모듈

KIS REST API 응답 코드를 분석하여 에러의 성격을 분류한다.
TRANSIENT: 재시도 가능 (네트워크 오류, 서버 과부하 등)
PERMANENT: 재시도 불가 (잘못된 파라미터, 권한 없음 등)
RATE_LIMIT: 속도 제한 초과
AUTH: 인증 오류 (토큰 만료 등)
"""

import logging
from typing import Optional

import httpx

from sv_core.broker.models import ErrorCategory

logger = logging.getLogger(__name__)

# KIS 응답 코드 → ErrorCategory 매핑
# KIS API는 HTTP 상태 코드 + rt_cd(응답 코드)를 함께 반환
_RT_CD_CATEGORY: dict[str, ErrorCategory] = {
    "0": ErrorCategory.TRANSIENT,   # 정상 (분류 필요 없음, 여기선 예외 처리 전용)
    "1": ErrorCategory.PERMANENT,   # 실패 (일반적 에러)
}

# HTTP 상태 코드 → ErrorCategory 매핑
_HTTP_STATUS_CATEGORY: dict[int, ErrorCategory] = {
    400: ErrorCategory.PERMANENT,   # Bad Request — 파라미터 오류
    401: ErrorCategory.AUTH,        # Unauthorized — 인증 실패
    403: ErrorCategory.PERMANENT,   # Forbidden — 권한 없음
    404: ErrorCategory.PERMANENT,   # Not Found
    429: ErrorCategory.RATE_LIMIT,  # Too Many Requests
    500: ErrorCategory.TRANSIENT,   # Internal Server Error — 재시도 가능
    502: ErrorCategory.TRANSIENT,   # Bad Gateway
    503: ErrorCategory.TRANSIENT,   # Service Unavailable
    504: ErrorCategory.TRANSIENT,   # Gateway Timeout
}

# KIS msg_cd 기반 세부 분류 (일부 주요 코드)
# 실제 KIS API 문서 기반으로 확장 필요
_MSG_CD_CATEGORY: dict[str, ErrorCategory] = {
    "EGW00123": ErrorCategory.AUTH,        # 접근 토큰 만료
    "EGW00121": ErrorCategory.AUTH,        # 접근 토큰 오류
    "EGW00201": ErrorCategory.RATE_LIMIT,  # 초당 요청 수 초과
    "EGW00202": ErrorCategory.RATE_LIMIT,  # 일일 요청 수 초과
    "OPSQ0008": ErrorCategory.PERMANENT,   # 종목 코드 오류
    "OPSQ0009": ErrorCategory.PERMANENT,   # 주문 수량 오류
    "OPSQ0010": ErrorCategory.PERMANENT,   # 주문 가격 오류
}


class ErrorClassifier:
    """KIS API 에러 분류기.

    HTTP 응답 또는 응답 JSON에서 에러 카테고리를 결정한다.
    """

    def classify_http_error(self, exc: httpx.HTTPStatusError) -> ErrorCategory:
        """HTTP 상태 에러를 분류한다.

        Args:
            exc: httpx.HTTPStatusError 예외

        Returns:
            ErrorCategory: 에러 분류
        """
        status_code = exc.response.status_code
        category = _HTTP_STATUS_CATEGORY.get(status_code, ErrorCategory.UNKNOWN)
        logger.debug(
            "HTTP 에러 분류: status=%d → %s", status_code, category.value
        )
        return category

    def classify_api_response(self, response_json: dict) -> ErrorCategory:
        """KIS API 응답 JSON에서 에러를 분류한다.

        KIS API는 HTTP 200 응답이어도 rt_cd != '0'이면 에러다.

        Args:
            response_json: API 응답 JSON

        Returns:
            ErrorCategory: 에러 분류 (정상이면 TRANSIENT 반환, 호출자가 무시)
        """
        rt_cd = response_json.get("rt_cd", "0")
        msg_cd = response_json.get("msg_cd", "")

        if rt_cd == "0":
            return ErrorCategory.TRANSIENT  # 정상 — 호출자가 체크 안 함

        # msg_cd 우선 확인 (더 세부적)
        if msg_cd in _MSG_CD_CATEGORY:
            category = _MSG_CD_CATEGORY[msg_cd]
            logger.warning(
                "API 에러 분류: rt_cd=%s msg_cd=%s → %s (msg=%s)",
                rt_cd, msg_cd, category.value, response_json.get("msg1", ""),
            )
            return category

        # rt_cd 기반 분류
        category = _RT_CD_CATEGORY.get(rt_cd, ErrorCategory.UNKNOWN)
        logger.warning(
            "API 에러 분류: rt_cd=%s → %s (msg=%s)",
            rt_cd, category.value, response_json.get("msg1", ""),
        )
        return category

    def classify_exception(self, exc: Exception) -> ErrorCategory:
        """일반 예외를 분류한다.

        Args:
            exc: 예외 객체

        Returns:
            ErrorCategory: 에러 분류
        """
        if isinstance(exc, httpx.HTTPStatusError):
            return self.classify_http_error(exc)
        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            return ErrorCategory.TRANSIENT
        if isinstance(exc, httpx.HTTPError):
            return ErrorCategory.TRANSIENT
        logger.debug("미분류 예외: %s → UNKNOWN", type(exc).__name__)
        return ErrorCategory.UNKNOWN

    def is_retryable(self, category: ErrorCategory) -> bool:
        """재시도 가능한 에러인지 반환한다.

        Args:
            category: 에러 분류

        Returns:
            bool: 재시도 가능 여부
        """
        return category in {ErrorCategory.TRANSIENT, ErrorCategory.RATE_LIMIT}

    def needs_reauth(self, category: ErrorCategory) -> bool:
        """재인증이 필요한 에러인지 반환한다.

        Args:
            category: 에러 분류

        Returns:
            bool: 재인증 필요 여부
        """
        return category == ErrorCategory.AUTH
