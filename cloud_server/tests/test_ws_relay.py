"""WS Relay 테스트 (RM-1).

/ws/relay, /ws/remote 엔드포인트 인증 + RelayManager 유닛 테스트.
"""
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import WebSocketDisconnect

from cloud_server.core.security import create_jwt
from cloud_server.tests.conftest import _make_user, _TestSession


def _reset_singletons():
    """테스트 격리를 위해 relay/session 싱글톤 초기화."""
    import cloud_server.services.relay_manager as rm
    rm._relay_manager = None
    rm._session_manager = None


@pytest.fixture(autouse=True)
def _clean_singletons():
    _reset_singletons()
    yield
    _reset_singletons()


@pytest.fixture()
def _patch_db_session():
    """relay_manager의 get_db_session을 테스트 DB로 교체."""
    def _test_session():
        return _TestSession()
    with patch("cloud_server.services.relay_manager.get_db_session", _test_session):
        yield


@pytest.fixture()
def _mock_heartbeat():
    """record_heartbeat를 mock — DB 의존 제거."""
    result = {
        "rules_version": 0,
        "context_version": 1,
        "watchlist_version": 0,
        "stock_master_version": 0,
        "latest_version": "1.0.0",
        "min_version": "1.0.0",
        "download_url": "",
        "timestamp": "2026-03-25T12:00:00",
    }
    with patch(
        "cloud_server.services.relay_manager.get_db_session"
    ) as mock_db:
        # _handle_heartbeat 내부에서 record_heartbeat를 import하므로 그쪽도 패치
        with patch(
            "cloud_server.services.heartbeat_service.record_heartbeat",
            return_value=result,
        ):
            mock_db.return_value = _TestSession()
            yield


# ── 1. 인증 성공 (/ws/relay) ──


def test_relay_auth_success(client, db, _mock_heartbeat):
    """유효 JWT로 /ws/relay 연결 → heartbeat_ack 수신으로 연결 유지 확인."""
    user = _make_user(db)
    token = create_jwt(user.id, user.email)

    with client.websocket_connect("/ws/relay") as ws:
        ws.send_json({"type": "auth", "payload": {"token": token}})
        ws.send_json({
            "type": "heartbeat",
            "id": "hb-1",
            "payload": {"version": "1.0.0"},
        })
        ack = ws.receive_json()
        assert ack["type"] == "heartbeat_ack"


# ── 2. 인증 거부 — 잘못된 토큰 ──


def test_relay_auth_invalid_token(client):
    """변조된 JWT → 4001 close."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/relay") as ws:
            ws.send_json({"type": "auth", "payload": {"token": "bad.token.here"}})
            ws.receive_json()
    assert exc_info.value.code == 4001


# ── 3. 인증 거부 — auth가 아닌 메시지 ──


def test_relay_auth_wrong_type(client):
    """첫 메시지가 auth 타입이 아니면 4001 close."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/relay") as ws:
            ws.send_json({"type": "heartbeat", "payload": {}})
            ws.receive_json()
    assert exc_info.value.code == 4001


# ── 4. /ws/remote — device_id 누락 ──


def test_remote_auth_missing_device_id(client, db):
    """device_id 없이 /ws/remote 연결 시 4002 close."""
    user = _make_user(db)
    token = create_jwt(user.id, user.email)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/remote") as ws:
            ws.send_json({"type": "auth", "payload": {"token": token}})
            ws.receive_json()
    assert exc_info.value.code == 4002


# ── 5. 명령 전달 (RelayManager 유닛 테스트) ──


@pytest.mark.asyncio
async def test_command_relay_to_local():
    """device command → RelayManager가 local WS로 전달."""
    from cloud_server.services.relay_manager import RelayManager

    relay = RelayManager()

    mock_local_ws = AsyncMock()
    relay.register_local("user-1", mock_local_ws)

    msg = {
        "type": "command",
        "id": "cmd-1",
        "payload": {"action": "kill", "mode": "stop_new"},
    }
    result = await relay.send_to_local("user-1", msg)

    assert result is True
    mock_local_ws.send_json.assert_called_once_with(msg)


# ── 6. 오프라인 큐 저장 (RelayManager 유닛 테스트) ──


def test_offline_queue_saves_pending(db, _patch_db_session):
    """local 미연결 → _save_pending_command가 DB에 저장."""
    from cloud_server.services.relay_manager import RelayManager

    user = _make_user(db)
    relay = RelayManager()

    relay._save_pending_command(str(user.id), "dev-1", {
        "type": "command",
        "id": "cmd-offline",
        "payload": {"action": "kill", "mode": "stop_all"},
    })

    from cloud_server.models.pending_command import PendingCommand
    pending = db.query(PendingCommand).filter(
        PendingCommand.user_id == str(user.id),
        PendingCommand.status == "pending",
    ).all()
    assert len(pending) == 1
    assert pending[0].command_type == "kill"


# ── 7. 오프라인 큐 flush ──


def test_offline_queue_flush_on_reconnect(client, db, _patch_db_session):
    """pending 명령 존재 → local 연결 시 자동 flush."""
    user = _make_user(db)
    token = create_jwt(user.id, user.email)

    from cloud_server.models.pending_command import PendingCommand
    cmd = PendingCommand(
        user_id=str(user.id),
        command_type="arm",
        payload={"action": "arm"},
        status="pending",
    )
    db.add(cmd)
    db.commit()

    with client.websocket_connect("/ws/relay") as ws:
        ws.send_json({"type": "auth", "payload": {"token": token}})
        msg = ws.receive_json()
        assert msg["type"] == "command"
        assert "pending-" in msg["id"]
        assert msg["payload"]["action"] == "arm"

    db.expire_all()
    updated = db.query(PendingCommand).filter(PendingCommand.id == cmd.id).first()
    assert updated.status == "executed"


# ── 8. heartbeat 라우팅 ──


def test_heartbeat_ack(client, db, _mock_heartbeat):
    """local이 heartbeat 전송 → heartbeat_ack 수신."""
    user = _make_user(db)
    token = create_jwt(user.id, user.email)

    with client.websocket_connect("/ws/relay") as ws:
        ws.send_json({"type": "auth", "payload": {"token": token}})
        ws.send_json({
            "type": "heartbeat",
            "id": "hb-test",
            "payload": {"version": "1.0.0"},
        })
        ack = ws.receive_json()
        assert ack["type"] == "heartbeat_ack"
        assert ack["id"] == "hb-test"
