"""
클라우드 인증 클라이언트 (로컬 서버용)

역할:
- token.dat에서 Refresh Token 관리 (load / save)
- 자동 시작 시 JWT 갱신 (refresh_jwt)
- 설정 조회 (get_config)
"""
import os
from pathlib import Path

import httpx

_CLOUD_URL = os.environ.get("CLOUD_URL", "https://stockvision.app")
_TOKEN_DAT = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "StockVision" / "token.dat"


class NeedsLoginError(Exception):
    """사용자 재로그인이 필요한 상태"""


class AuthClient:
    def load_refresh_token(self) -> str | None:
        if _TOKEN_DAT.exists():
            return _TOKEN_DAT.read_text(encoding="utf-8").strip()
        return None

    def save_refresh_token(self, token: str) -> None:
        _TOKEN_DAT.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_DAT.write_text(token, encoding="utf-8")

    def delete_refresh_token(self) -> None:
        if _TOKEN_DAT.exists():
            _TOKEN_DAT.unlink()

    def refresh_jwt(self) -> str:
        """token.dat → 새 JWT 발급. 실패 시 NeedsLoginError"""
        rt = self.load_refresh_token()
        if not rt:
            raise NeedsLoginError("token.dat가 없습니다. 로그인이 필요합니다.")

        try:
            resp = httpx.post(
                f"{_CLOUD_URL}/api/auth/refresh",
                json={"refresh_token": rt},
                timeout=10,
            )
        except httpx.RequestError as e:
            raise NeedsLoginError(f"클라우드 서버 연결 실패: {e}") from e

        if resp.status_code == 401:
            self.delete_refresh_token()
            raise NeedsLoginError("Refresh Token이 만료되었습니다. 재로그인이 필요합니다.")

        resp.raise_for_status()
        data = resp.json()
        self.save_refresh_token(data["refresh_token"])  # Rotation
        return data["jwt"]

    def get_config(self, jwt: str) -> dict:
        """클라우드에서 사용자 설정 조회"""
        resp = httpx.get(
            f"{_CLOUD_URL}/api/v1/config",
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    def save_token_from_login(self, jwt: str, refresh_token: str) -> None:
        """React에서 로그인 후 JWT+RT 전달 시 저장 (POST /api/config/unlock 용)"""
        self.save_refresh_token(refresh_token)
