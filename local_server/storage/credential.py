"""브로커 API 자격증명 + 클라우드 토큰 저장소.

Windows Keyring을 사용하여 API Key / Secret 및 클라우드 JWT 토큰을 암호화 저장한다.
user_id 네임스페이스로 동일 PC 내 멀티유저를 격리한다.
keyring이 사용 불가능한 환경에서는 CredentialError를 발생시킨다.
"""
from __future__ import annotations

import logging

import keyring
import keyring.errors

logger = logging.getLogger(__name__)

# keyring 서비스 이름 접두사 — user_id와 조합하여 격리
_SERVICE_PREFIX = "stockvision"
_DEFAULT_USER = "default"

# 활성 사용자 — 로그인 시 JWT에서 email을 추출하여 설정
_active_user: str = _DEFAULT_USER


def set_active_user(user_id: str) -> None:
    """로그인 시 활성 사용자를 설정한다. 이후 모든 credential 함수가 이 네임스페이스를 사용한다."""
    global _active_user
    _active_user = user_id
    from local_server.config import get_config
    cfg = get_config()
    cfg.set("auth.last_user", user_id)
    cfg.save()
    logger.info("활성 사용자 설정: %s", user_id)


def _restore_active_user(user_id: str) -> None:
    """서버 시작 시 config에서 복원 — config 재저장 안 함, 메모리만."""
    global _active_user
    _active_user = user_id
    logger.info("활성 사용자 복원: %s", user_id)


def get_active_user() -> str:
    """현재 활성 사용자 ID를 반환한다."""
    return _active_user

# keyring 키 이름 상수 — KIS API
KEY_APP_KEY = "kis_app_key"
KEY_APP_SECRET = "kis_app_secret"
KEY_ACCESS_TOKEN = "kis_access_token"
KEY_ACCOUNT_NO = "kis_account_no"

# keyring 키 이름 상수 — 키움 API
KEY_KIWOOM_APP_KEY = "kiwoom_app_key"
KEY_KIWOOM_SECRET_KEY = "kiwoom_secret_key"

# keyring 키 이름 상수 — 클라우드 JWT
KEY_CLOUD_ACCESS_TOKEN = "sv_cloud_access_token"
KEY_CLOUD_REFRESH_TOKEN = "sv_cloud_refresh_token"


def _service_name(user_id: str = _DEFAULT_USER) -> str:
    """user_id별 격리된 keyring 서비스 이름을 반환한다."""
    return f"{_SERVICE_PREFIX}:{user_id}"


class CredentialError(Exception):
    """자격증명 저장/조회 실패 시 발생하는 예외."""


def save_credential(name: str, value: str, user_id: str | None = None) -> None:
    """자격증명을 keyring에 저장한다.

    Args:
        name: 자격증명 이름 (예: KEY_APP_KEY)
        value: 저장할 값
        user_id: 사용자 식별자 (None이면 활성 사용자 사용)
    """
    svc = _service_name(user_id or _active_user)
    try:
        keyring.set_password(svc, name, value)
        logger.debug("자격증명 저장 완료: %s (user=%s)", name, user_id)
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 저장 실패 ({name}): {e}") from e


def load_credential(name: str, user_id: str | None = None) -> str | None:
    """keyring에서 자격증명을 조회한다.

    Args:
        name: 자격증명 이름
        user_id: 사용자 식별자 (None이면 활성 사용자 사용)

    Returns:
        저장된 값, 없으면 None
    """
    svc = _service_name(user_id or _active_user)
    try:
        return keyring.get_password(svc, name)
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 조회 실패 ({name}): {e}") from e


def delete_credential(name: str, user_id: str | None = None) -> None:
    """keyring에서 자격증명을 삭제한다.

    Args:
        name: 자격증명 이름
        user_id: 사용자 식별자 (None이면 활성 사용자 사용)
    """
    svc = _service_name(user_id or _active_user)
    try:
        keyring.delete_password(svc, name)
        logger.debug("자격증명 삭제 완료: %s (user=%s)", name, user_id)
    except keyring.errors.PasswordDeleteError:
        pass
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 삭제 실패 ({name}): {e}") from e


def has_credential(name: str, user_id: str | None = None) -> bool:
    """자격증명이 저장되어 있는지 확인한다."""
    return load_credential(name, user_id) is not None


def save_api_keys(app_key: str, app_secret: str, user_id: str | None = None) -> None:
    """KIS 앱 키와 시크릿을 저장한다."""
    save_credential(KEY_APP_KEY, app_key, user_id)
    save_credential(KEY_APP_SECRET, app_secret, user_id)


def load_api_keys(user_id: str | None = None) -> tuple[str | None, str | None]:
    """KIS 앱 키와 시크릿을 반환한다."""
    return load_credential(KEY_APP_KEY, user_id), load_credential(KEY_APP_SECRET, user_id)


def save_access_token(token: str, user_id: str | None = None) -> None:
    """발급받은 액세스 토큰을 저장한다."""
    save_credential(KEY_ACCESS_TOKEN, token, user_id)


def load_access_token(user_id: str | None = None) -> str | None:
    """저장된 액세스 토큰을 반환한다."""
    return load_credential(KEY_ACCESS_TOKEN, user_id)


# ── 클라우드 JWT 토큰 ────────────────────────────────────────────────────────


def save_cloud_tokens(access_token: str, refresh_token: str, user_id: str | None = None) -> None:
    """클라우드 로그인 후 전달받은 JWT 토큰 쌍을 keyring에 저장한다."""
    save_credential(KEY_CLOUD_ACCESS_TOKEN, access_token, user_id)
    save_credential(KEY_CLOUD_REFRESH_TOKEN, refresh_token, user_id)


def load_cloud_tokens(user_id: str | None = None) -> tuple[str | None, str | None]:
    """저장된 클라우드 JWT 토큰 쌍을 반환한다. (access, refresh)"""
    return (
        load_credential(KEY_CLOUD_ACCESS_TOKEN, user_id),
        load_credential(KEY_CLOUD_REFRESH_TOKEN, user_id),
    )


# ── KIS 계좌번호 ─────────────────────────────────────────────────────────────


def save_account_no(account_no: str, user_id: str | None = None) -> None:
    """KIS 계좌번호를 keyring에 저장한다."""
    save_credential(KEY_ACCOUNT_NO, account_no, user_id)


def load_account_no(user_id: str | None = None) -> str | None:
    """저장된 KIS 계좌번호를 반환한다."""
    return load_credential(KEY_ACCOUNT_NO, user_id)


def clear_session_credentials(user_id: str | None = None) -> None:
    """세션 토큰만 삭제한다 (로그아웃 시 사용). 브로커 API 키는 보존."""
    for name in (
        KEY_CLOUD_ACCESS_TOKEN,
        KEY_CLOUD_REFRESH_TOKEN,
        KEY_ACCESS_TOKEN,  # KIS 액세스 토큰 (세션성)
    ):
        delete_credential(name, user_id)
    logger.info("세션 자격증명 삭제 완료 (user=%s)", user_id)


def clear_all_credentials(user_id: str | None = None) -> None:
    """해당 사용자의 모든 자격증명을 삭제한다 (계정 초기화 시 사용)."""
    for name in (
        KEY_APP_KEY,
        KEY_APP_SECRET,
        KEY_ACCESS_TOKEN,
        KEY_ACCOUNT_NO,
        KEY_KIWOOM_APP_KEY,
        KEY_KIWOOM_SECRET_KEY,
        KEY_CLOUD_ACCESS_TOKEN,
        KEY_CLOUD_REFRESH_TOKEN,
    ):
        delete_credential(name, user_id)
    logger.info("모든 자격증명 삭제 완료 (user=%s)", user_id)
