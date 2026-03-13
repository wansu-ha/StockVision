"""local_server 테스트 공통 픽스처.

test_routers.py에서 추출한 픽스처들.
- tmp_config: 임시 설정 파일을 사용하는 Config 픽스처
- client: TestClient 픽스처 (keyring mock)
- sh: 보호 엔드포인트용 X-Local-Secret 헤더
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """임시 설정 파일을 사용하는 Config 픽스처."""
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("SV_CONFIG_PATH", str(config_file))

    # 전역 싱글턴 리셋
    import local_server.config as cfg_module
    cfg_module._config_instance = None

    import local_server.storage.rules_cache as rc_module
    rc_module._rules_cache_instance = None

    import local_server.storage.log_db as ld_module
    ld_module._log_db_instance = None

    yield tmp_path

    # 테스트 후 싱글턴 리셋
    cfg_module._config_instance = None
    rc_module._rules_cache_instance = None
    ld_module._log_db_instance = None


@pytest.fixture
def client(tmp_config: Path):
    """TestClient 픽스처. keyring은 mock으로 대체."""
    with patch("keyring.get_password", return_value=None), \
         patch("keyring.set_password"), \
         patch("keyring.delete_password"):

        # log_db, rules_cache가 tmp 경로 사용하도록 패치
        from local_server.storage.log_db import LogDB
        import local_server.storage.log_db as ld_module
        ld_module._log_db_instance = LogDB(db_path=tmp_config / "logs.db")

        from local_server.storage.rules_cache import RulesCache
        import local_server.storage.rules_cache as rc_module
        rc_module._rules_cache_instance = RulesCache(rules_path=tmp_config / "rules.json")

        from local_server.main import create_app
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            # shared secret 헤더를 client에 부착
            c._local_secret = app.state.local_secret
            yield c


@pytest.fixture
def sh(client: TestClient) -> dict[str, str]:
    """보호 엔드포인트용 X-Local-Secret 헤더."""
    return {"X-Local-Secret": client._local_secret}
