"""설정 파일 저장소.

config.py의 Config 클래스를 감싸 API 레이어에서 편리하게 사용할 수 있는
헬퍼 함수를 제공한다.
"""
from __future__ import annotations

from typing import Any

from local_server.config import get_config


def read_config() -> dict[str, Any]:
    """현재 설정을 딕셔너리로 반환한다.

    민감 정보(kis.app_key, app_secret)는 마스킹하여 반환한다.
    """
    cfg = get_config()
    data = cfg.as_dict()

    # 민감 정보 마스킹
    kis = data.get("kis", {})
    if kis.get("app_key"):
        kis["app_key"] = "****"
    if kis.get("app_secret"):
        kis["app_secret"] = "****"

    return data


def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    """설정을 업데이트하고 저장한 후, 마스킹된 설정을 반환한다.

    Args:
        updates: 변경할 설정 딕셔너리 (중첩 가능)

    Returns:
        업데이트된 설정 (민감 정보 마스킹)
    """
    # 민감 정보가 평문으로 오면 keyring에 저장하고 config에서 제거
    kis_updates = updates.get("kis", {})
    app_key = kis_updates.pop("app_key", None)
    app_secret = kis_updates.pop("app_secret", None)

    if app_key or app_secret:
        from local_server.storage.credential import save_api_keys, load_api_keys
        existing_key, existing_secret = load_api_keys()
        save_api_keys(
            app_key or existing_key or "",
            app_secret or existing_secret or "",
        )

    cfg = get_config()
    cfg.update(updates)
    cfg.save()

    return read_config()
