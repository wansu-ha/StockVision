"""키움 API 자격증명 + 클라우드 토큰 저장소.

Windows Keyring을 사용하여 API Key / Secret 및 클라우드 JWT 토큰을 암호화 저장한다.
keyring이 사용 불가능한 환경에서는 CredentialError를 발생시킨다.
"""
from __future__ import annotations

import logging

import keyring
import keyring.errors

logger = logging.getLogger(__name__)

# keyring 서비스 이름
_SERVICE_NAME = "stockvision-local-server"

# keyring 키 이름 상수 — 키움 API
KEY_APP_KEY = "kiwoom_app_key"
KEY_APP_SECRET = "kiwoom_app_secret"
KEY_ACCESS_TOKEN = "kiwoom_access_token"
KEY_ACCOUNT_NO = "kiwoom_account_no"

# keyring 키 이름 상수 — 클라우드 JWT
KEY_CLOUD_ACCESS_TOKEN = "sv_cloud_access_token"
KEY_CLOUD_REFRESH_TOKEN = "sv_cloud_refresh_token"


class CredentialError(Exception):
    """자격증명 저장/조회 실패 시 발생하는 예외."""


def save_credential(name: str, value: str) -> None:
    """자격증명을 keyring에 저장한다.

    Args:
        name: 자격증명 이름 (예: KEY_APP_KEY)
        value: 저장할 값
    """
    try:
        keyring.set_password(_SERVICE_NAME, name, value)
        logger.debug("자격증명 저장 완료: %s", name)
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 저장 실패 ({name}): {e}") from e


def load_credential(name: str) -> str | None:
    """keyring에서 자격증명을 조회한다.

    Args:
        name: 자격증명 이름

    Returns:
        저장된 값, 없으면 None
    """
    try:
        value = keyring.get_password(_SERVICE_NAME, name)
        return value
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 조회 실패 ({name}): {e}") from e


def delete_credential(name: str) -> None:
    """keyring에서 자격증명을 삭제한다.

    Args:
        name: 자격증명 이름
    """
    try:
        keyring.delete_password(_SERVICE_NAME, name)
        logger.debug("자격증명 삭제 완료: %s", name)
    except keyring.errors.PasswordDeleteError:
        # 이미 없는 경우 무시
        pass
    except keyring.errors.KeyringError as e:
        raise CredentialError(f"자격증명 삭제 실패 ({name}): {e}") from e


def has_credential(name: str) -> bool:
    """자격증명이 저장되어 있는지 확인한다."""
    return load_credential(name) is not None


def save_api_keys(app_key: str, app_secret: str) -> None:
    """키움 앱 키와 시크릿을 저장한다."""
    save_credential(KEY_APP_KEY, app_key)
    save_credential(KEY_APP_SECRET, app_secret)


def load_api_keys() -> tuple[str | None, str | None]:
    """키움 앱 키와 시크릿을 반환한다."""
    return load_credential(KEY_APP_KEY), load_credential(KEY_APP_SECRET)


def save_access_token(token: str) -> None:
    """발급받은 액세스 토큰을 저장한다."""
    save_credential(KEY_ACCESS_TOKEN, token)


def load_access_token() -> str | None:
    """저장된 액세스 토큰을 반환한다."""
    return load_credential(KEY_ACCESS_TOKEN)


# ── 클라우드 JWT 토큰 ────────────────────────────────────────────────────────


def save_cloud_tokens(access_token: str, refresh_token: str) -> None:
    """클라우드 로그인 후 전달받은 JWT 토큰 쌍을 keyring에 저장한다."""
    save_credential(KEY_CLOUD_ACCESS_TOKEN, access_token)
    save_credential(KEY_CLOUD_REFRESH_TOKEN, refresh_token)


def load_cloud_tokens() -> tuple[str | None, str | None]:
    """저장된 클라우드 JWT 토큰 쌍을 반환한다. (access, refresh)"""
    return (
        load_credential(KEY_CLOUD_ACCESS_TOKEN),
        load_credential(KEY_CLOUD_REFRESH_TOKEN),
    )


# ── 키움 계좌번호 ────────────────────────────────────────────────────────────


def save_account_no(account_no: str) -> None:
    """키움 계좌번호를 keyring에 저장한다."""
    save_credential(KEY_ACCOUNT_NO, account_no)


def load_account_no() -> str | None:
    """저장된 키움 계좌번호를 반환한다."""
    return load_credential(KEY_ACCOUNT_NO)


def clear_all_credentials() -> None:
    """모든 자격증명을 삭제한다 (로그아웃 시 사용)."""
    for name in (
        KEY_APP_KEY,
        KEY_APP_SECRET,
        KEY_ACCESS_TOKEN,
        KEY_ACCOUNT_NO,
        KEY_CLOUD_ACCESS_TOKEN,
        KEY_CLOUD_REFRESH_TOKEN,
    ):
        delete_credential(name)
    logger.info("모든 자격증명 삭제 완료")
