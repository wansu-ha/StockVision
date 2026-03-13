"""레거시 제거 검증 테스트.

CT-7: 프론트엔드에서 레거시 백엔드 참조 제거 확인
"""
from __future__ import annotations

import re
from pathlib import Path


# 프론트엔드 소스 루트
FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"


class TestLegacyRemoval:
    """CT-7: 레거시 참조 제거 검증."""

    def test_ct7a_no_localhost_8000_in_frontend(self):
        """CT-7a: frontend/src/ 내 localhost:8000 실제 URL 참조 0건.

        주석 내 언급은 허용, 실제 URL 패턴(http://localhost:8000)만 검사.
        """
        # http://localhost:8000 또는 'localhost:8000' (URL로 사용되는 패턴)
        url_pattern = re.compile(r"""(?:https?://|['"`])localhost:8000""")

        violations: list[str] = []
        for path in FRONTEND_SRC.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                # 주석 라인은 건너뜀 (// 또는 * 로 시작하는 줄)
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                    continue
                if url_pattern.search(line):
                    violations.append(f"{path.relative_to(FRONTEND_SRC)}:{i}: {line.strip()}")

        assert not violations, (
            f"frontend/src/에 localhost:8000 참조 {len(violations)}건 발견:\n"
            + "\n".join(violations)
        )
