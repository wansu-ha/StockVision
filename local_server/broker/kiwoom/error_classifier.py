"""local_server.broker.kiwoom.error_classifier: 키움 API 에러 분류 모듈

키움 REST API 응답의 return_code를 분석하여 에러 성격을 분류한다.
KIS와 차이: return_code (int, 0=성공) vs rt_cd (str, "0"=성공)
"""

import logging

import httpx

from sv_core.broker.models import ErrorCategory

logger = logging.getLogger(__name__)

# HTTP 상태 코드 → ErrorCategory 매핑
_HTTP_STATUS_CATEGORY: dict[int, ErrorCategory] = {
    400: ErrorCategory.PERMANENT,
    401: ErrorCategory.AUTH,
    403: ErrorCategory.PERMANENT,
    404: ErrorCategory.PERMANENT,
    429: ErrorCategory.RATE_LIMIT,
    500: ErrorCategory.TRANSIENT,
    502: ErrorCategory.TRANSIENT,
    503: ErrorCategory.TRANSIENT,
    504: ErrorCategory.TRANSIENT,
}


class KiwoomErrorClassifier:
    """키움 API 에러 분류기."""

    def classify_http_error(self, exc: httpx.HTTPStatusError) -> ErrorCategory:
        status_code = exc.response.status_code
        category = _HTTP_STATUS_CATEGORY.get(status_code, ErrorCategory.UNKNOWN)
        logger.debug("HTTP 에러 분류: status=%d → %s", status_code, category.value)
        return category

    def classify_api_response(self, response_json: dict) -> ErrorCategory:
        """키움 API 응답 JSON에서 에러를 분류한다.

        키움은 return_code == 0이 성공, 그 외는 에러.
        """
        return_code = response_json.get("return_code", 0)
        if return_code == 0:
            return ErrorCategory.TRANSIENT  # 정상

        return_msg = response_json.get("return_msg", "")
        # 키움은 세부 에러 코드가 없으므로 메시지 기반 분류
        if "토큰" in return_msg or "인증" in return_msg or "token" in return_msg.lower():
            category = ErrorCategory.AUTH
        elif "초과" in return_msg or "제한" in return_msg:
            category = ErrorCategory.RATE_LIMIT
        else:
            category = ErrorCategory.PERMANENT

        logger.warning(
            "API 에러 분류: return_code=%d → %s (msg=%s)",
            return_code, category.value, return_msg,
        )
        return category

    def classify_exception(self, exc: Exception) -> ErrorCategory:
        if isinstance(exc, httpx.HTTPStatusError):
            return self.classify_http_error(exc)
        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            return ErrorCategory.TRANSIENT
        if isinstance(exc, httpx.HTTPError):
            return ErrorCategory.TRANSIENT
        return ErrorCategory.UNKNOWN

    def is_retryable(self, category: ErrorCategory) -> bool:
        return category in {ErrorCategory.TRANSIENT, ErrorCategory.RATE_LIMIT}

    def needs_reauth(self, category: ErrorCategory) -> bool:
        return category == ErrorCategory.AUTH
