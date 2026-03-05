"""저장소 레이어 테스트.

실제 keyring 대신 mock을 사용하고,
임시 파일 경로를 사용하여 사이드이펙트 없이 테스트한다.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────
# Config 테스트
# ──────────────────────────────────────────────────────

class TestConfig:
    def test_default_config_loaded_when_no_file(self, tmp_path: Path) -> None:
        """설정 파일이 없으면 기본값으로 초기화된다."""
        from local_server.config import Config
        cfg = Config(config_path=tmp_path / "config.json")
        assert cfg.get("server.port") == 4020
        assert cfg.get("sleep_prevent") is True

    def test_get_nested_key(self, tmp_path: Path) -> None:
        """점 표기법으로 중첩 설정값을 가져온다."""
        from local_server.config import Config
        cfg = Config(config_path=tmp_path / "config.json")
        assert cfg.get("server.host") == "127.0.0.1"

    def test_set_and_save(self, tmp_path: Path) -> None:
        """설정을 변경하고 저장한 후 다시 로드하면 동일한 값이 반환된다."""
        from local_server.config import Config
        config_file = tmp_path / "config.json"

        cfg = Config(config_path=config_file)
        cfg.set("server.port", 9999)
        cfg.save()

        # 새 인스턴스로 다시 로드
        cfg2 = Config(config_path=config_file)
        assert cfg2.get("server.port") == 9999

    def test_merge_preserves_defaults(self, tmp_path: Path) -> None:
        """파일에 일부 키만 있어도 기본값이 보존된다."""
        from local_server.config import Config
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"server": {"port": 1234}}), encoding="utf-8")

        cfg = Config(config_path=config_file)
        # 파일에 있는 값
        assert cfg.get("server.port") == 1234
        # 기본값 보존
        assert cfg.get("server.host") == "127.0.0.1"
        assert cfg.get("sleep_prevent") is True

    def test_get_missing_key_returns_default(self, tmp_path: Path) -> None:
        """존재하지 않는 키는 default를 반환한다."""
        from local_server.config import Config
        cfg = Config(config_path=tmp_path / "config.json")
        assert cfg.get("nonexistent.key", "fallback") == "fallback"

    def test_update_and_as_dict(self, tmp_path: Path) -> None:
        """update()로 여러 키를 한 번에 변경하고 as_dict()로 확인한다."""
        from local_server.config import Config
        cfg = Config(config_path=tmp_path / "config.json")
        cfg.update({"log_level": "DEBUG", "server": {"port": 7777}})
        d = cfg.as_dict()
        assert d["log_level"] == "DEBUG"
        assert d["server"]["port"] == 7777


# ──────────────────────────────────────────────────────
# RulesCache 테스트
# ──────────────────────────────────────────────────────

class TestRulesCache:
    def test_empty_on_missing_file(self, tmp_path: Path) -> None:
        """파일이 없으면 빈 규칙 목록으로 시작한다."""
        from local_server.storage.rules_cache import RulesCache
        cache = RulesCache(rules_path=tmp_path / "rules.json")
        assert cache.get_rules() == []
        assert cache.count() == 0

    def test_sync_saves_and_loads(self, tmp_path: Path) -> None:
        """sync() 후 파일에 저장되고, 새 인스턴스에서 동일한 값이 로드된다."""
        from local_server.storage.rules_cache import RulesCache
        rules_file = tmp_path / "rules.json"

        cache = RulesCache(rules_path=rules_file)
        rules = [{"id": 1, "name": "RSI매수"}, {"id": 2, "name": "EMA매도"}]
        cache.sync(rules)
        assert cache.count() == 2

        # 재로드
        cache2 = RulesCache(rules_path=rules_file)
        assert cache2.count() == 2
        assert cache2.get_rules()[0]["name"] == "RSI매수"

    def test_sync_replaces_all(self, tmp_path: Path) -> None:
        """sync()는 기존 규칙을 완전히 교체한다."""
        from local_server.storage.rules_cache import RulesCache
        rules_file = tmp_path / "rules.json"

        cache = RulesCache(rules_path=rules_file)
        cache.sync([{"id": 1}])
        cache.sync([{"id": 2}, {"id": 3}])
        assert cache.count() == 2
        assert cache.get_rules()[0]["id"] == 2


# ──────────────────────────────────────────────────────
# LogDB 테스트
# ──────────────────────────────────────────────────────

class TestLogDB:
    def test_write_and_query(self, tmp_path: Path) -> None:
        """로그를 기록하고 조회한다."""
        from local_server.storage.log_db import LogDB, LOG_TYPE_ORDER

        db = LogDB(db_path=tmp_path / "logs.db")
        row_id = db.write(LOG_TYPE_ORDER, "테스트 주문", symbol="005930")
        assert isinstance(row_id, int)
        assert row_id > 0

        items, total = db.query()
        assert total == 1
        assert items[0]["message"] == "테스트 주문"
        assert items[0]["symbol"] == "005930"

    def test_query_filter_by_type(self, tmp_path: Path) -> None:
        """log_type으로 필터링한다."""
        from local_server.storage.log_db import LogDB, LOG_TYPE_ORDER, LOG_TYPE_ERROR

        db = LogDB(db_path=tmp_path / "logs.db")
        db.write(LOG_TYPE_ORDER, "주문")
        db.write(LOG_TYPE_ERROR, "에러")

        items, total = db.query(log_type=LOG_TYPE_ORDER)
        assert total == 1
        assert items[0]["log_type"] == LOG_TYPE_ORDER

    def test_query_pagination(self, tmp_path: Path) -> None:
        """limit/offset 페이지네이션이 동작한다."""
        from local_server.storage.log_db import LogDB, LOG_TYPE_SYSTEM

        db = LogDB(db_path=tmp_path / "logs.db")
        for i in range(5):
            db.write(LOG_TYPE_SYSTEM, f"로그{i}")

        items, total = db.query(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2

        items2, _ = db.query(limit=2, offset=2)
        assert len(items2) == 2

    def test_meta_stored_and_retrieved(self, tmp_path: Path) -> None:
        """meta 딕셔너리가 JSON으로 저장되고 역직렬화되어 반환된다."""
        from local_server.storage.log_db import LogDB, LOG_TYPE_FILL

        db = LogDB(db_path=tmp_path / "logs.db")
        meta = {"price": 75000, "qty": 10}
        db.write(LOG_TYPE_FILL, "체결", meta=meta)

        items, _ = db.query()
        assert items[0]["meta"] == meta


# ──────────────────────────────────────────────────────
# Credential 테스트 (keyring mock)
# ──────────────────────────────────────────────────────

class TestCredential:
    def test_save_and_load(self) -> None:
        """keyring에 자격증명을 저장하고 조회한다."""
        with patch("keyring.set_password") as mock_set, \
             patch("keyring.get_password", return_value="my_key") as mock_get:

            from local_server.storage.credential import save_credential, load_credential
            save_credential("test_key", "my_key")
            mock_set.assert_called_once()

            value = load_credential("test_key")
            mock_get.assert_called_once()
            assert value == "my_key"

    def test_has_credential_true_when_exists(self) -> None:
        """자격증명이 있으면 has_credential이 True를 반환한다."""
        with patch("keyring.get_password", return_value="exists"):
            from local_server.storage.credential import has_credential
            assert has_credential("some_key") is True

    def test_has_credential_false_when_missing(self) -> None:
        """자격증명이 없으면 has_credential이 False를 반환한다."""
        with patch("keyring.get_password", return_value=None):
            from local_server.storage.credential import has_credential
            assert has_credential("missing_key") is False

    def test_save_api_keys(self) -> None:
        """save_api_keys는 app_key와 app_secret을 각각 저장한다."""
        with patch("keyring.set_password") as mock_set:
            from local_server.storage.credential import save_api_keys
            save_api_keys("key123", "secret456")
            assert mock_set.call_count == 2
