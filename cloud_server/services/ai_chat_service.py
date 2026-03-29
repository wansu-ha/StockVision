"""AI 대화 서비스 — 전략 빌더 코파일럿 + 기본 비서.

Claude API 스트리밍 호출, DSL 검증 루프, 대화 히���토리 관리.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.models.ai_conversation import AIConversation
from cloud_server.prompts.strategy_builder import build_system_prompt, build_assistant_prompt
from cloud_server.services.credit_service import CreditService

logger = logging.getLogger(__name__)


class AIChatService:
    """AI 대화 처리."""

    def __init__(self, db: Session):
        self.db = db
        self.credit = CreditService(db)

    async def chat(
        self,
        *,
        conversation_id: str | None,
        message: str,
        current_dsl: str | None,
        mode: str,
        thinking: bool,
        user_id: str,
    ) -> AsyncGenerator[dict, None]:
        """대화 처리 → SSE 이벤트 스트림.

        Yields:
            {"event": "status|thinking|token|dsl|error|done", "data": {...}}
        """
        # 크레딧 확인 (비서 모드는 무료)
        is_byo = self.credit.is_byo_user(user_id)
        if mode == "builder" and not is_byo:
            balance = self.credit.get_balance(user_id)
            if balance["remaining_percent"] <= 0:
                yield {"event": "error", "data": {"code": "credit_exhausted", "message": "일일 크레딧이 소진되었습니다"}}
                return

        # 대화 히스토리 조회/생성
        conv = self._get_or_create_conversation(conversation_id, user_id, mode)

        # 사용자 메시지 추가
        conv.messages = conv.messages + [{"role": "user", "content": message, "timestamp": datetime.now(timezone.utc).isoformat()}]
        if not conv.title and len(conv.messages) == 1:
            conv.title = message[:100]

        yield {"event": "status", "data": {"step": "analyzing", "message": "전략 분석 중..."}}

        # API 키 결정
        api_key = self.credit.get_byo_key(user_id) if is_byo else settings.ANTHROPIC_API_KEY
        if not api_key:
            yield {"event": "error", "data": {"code": "api_error", "message": "API 키가 설정��지 않았습니다"}}
            return

        # 모델/프롬프트 결정
        if mode == "assistant":
            model = settings.CLAUDE_MODEL_ASSISTANT
            system_prompt = build_assistant_prompt()
        else:
            model = settings.CLAUDE_MODEL
            system_prompt = build_system_prompt()

        # LLM 메시지 구성 (윈도우)
        llm_messages = self._build_window(conv.messages, current_dsl)

        yield {"event": "status", "data": {"step": "generating", "message": "DSL ��성 중..."}}

        # Claude API 스트리밍 호출
        full_response = ""
        total_input = 0
        total_output = 0
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

            create_kwargs = {
                "model": model,
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": llm_messages,
            }
            if thinking and mode == "builder":
                create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4096}

            with client.messages.stream(**create_kwargs) as stream:
                for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "thinking"):
                                yield {"event": "thinking", "data": {"content": event.delta.thinking}}
                            elif hasattr(event.delta, "text"):
                                full_response += event.delta.text
                                yield {"event": "token", "data": {"content": event.delta.text}}

                # 사용량
                usage = stream.get_final_message().usage
                total_input = usage.input_tokens
                total_output = usage.output_tokens

        except Exception as e:
            logger.error("Claude API 스트리밍 실패: %s", e)
            yield {"event": "error", "data": {"code": "api_error", "message": "AI 서비스에 일시적 오류가 발생했습니다"}}
            return

        # DSL 추출 + 검증 (빌더 모드만)
        dsl_script = None
        if mode == "builder":
            dsl_script = self._extract_dsl(full_response)
            if dsl_script:
                yield {"event": "status", "data": {"step": "validating", "message": "문법 검증 ��..."}}
                validated, retry_tokens = await self._validate_with_retry(
                    dsl_script, client, model, system_prompt, llm_messages, full_response
                )
                if validated:
                    dsl_script = validated
                    total_input += retry_tokens.get("input", 0)
                    total_output += retry_tokens.get("output", 0)
                yield {"event": "dsl", "data": {"script": dsl_script, "valid": validated is not None}}

        # 크레딧 차감 (재시도 토큰 제외, 빌더만)
        tokens_to_charge = total_input + total_output
        if mode == "builder" and not is_byo:
            try:
                self.credit.deduct(user_id, tokens_to_charge)
            except ValueError:
                pass  # 이미 응답은 보냈으므로 로그만

        # 어시스턴트 메시지 저장
        conv.messages = conv.messages + [{"role": "assistant", "content": full_response, "timestamp": datetime.now(timezone.utc).isoformat()}]
        if current_dsl or dsl_script:
            conv.current_dsl = dsl_script or current_dsl
        self.db.commit()

        # 완료 이벤트
        balance = self.credit.get_balance(user_id) if not is_byo else {"remaining_percent": 100, "estimate_turns": 999}
        yield {"event": "done", "data": {
            "conversation_id": conv.id,
            "credit_remaining": balance["remaining_percent"],
            "credit_estimate": f"약 {balance['estimate_turns']}회",
            "tokens_used": tokens_to_charge,
        }}

    def _get_or_create_conversation(self, conv_id: str | None, user_id: str, mode: str) -> AIConversation:
        """대화 조회 또는 생성."""
        if conv_id:
            conv = self.db.query(AIConversation).filter(
                AIConversation.id == conv_id,
                AIConversation.user_id == user_id,
            ).first()
            if conv:
                return conv
        conv = AIConversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            messages=[],
            mode=mode,
        )
        self.db.add(conv)
        self.db.flush()
        return conv

    def _build_window(self, messages: list[dict], current_dsl: str | None) -> list[dict]:
        """LLM 전송용 메시지 윈도우 구성."""
        llm_msgs = []
        if current_dsl:
            llm_msgs.append({"role": "user", "content": f"현재 DSL:\n```dsl\n{current_dsl}\n```"})
            llm_msgs.append({"role": "assistant", "content": "네, 현재 전략을 확인했습니다."})

        # 최근 N턴 (토큰 예산 내)
        budget = settings.AI_WINDOW_MAX_TOKENS
        used = 0
        window = []
        for msg in reversed(messages):
            est = len(msg["content"]) // 2  # 대략 2자 = 1토큰
            if used + est > budget:
                break
            window.append(msg)
            used += est
        window.reverse()

        for msg in window:
            llm_msgs.append({"role": msg["role"], "content": msg["content"]})
        return llm_msgs

    @staticmethod
    def _extract_dsl(response: str) -> str | None:
        """���답에서 ```dsl 블록 추출."""
        match = re.search(r"```dsl\s*\n(.*?)```", response, re.DOTALL)
        return match.group(1).strip() if match else None

    async def _validate_with_retry(
        self, dsl: str, client, model: str, system: str, messages: list, response: str
    ) -> tuple[str | None, dict]:
        """parse_v2 검증 + 실패 시 재시도. 반환: (검증된 DSL | None, 재시도 토큰)."""
        from sv_core.parsing.parser import parse_v2
        from sv_core.parsing.errors import DSLSyntaxError, DSLNameError

        retry_tokens = {"input": 0, "output": 0}

        for attempt in range(settings.AI_MAX_RETRIES):
            try:
                parse_v2(dsl)
                return dsl, retry_tokens
            except (DSLSyntaxError, DSLNameError) as e:
                if attempt >= settings.AI_MAX_RETRIES - 1:
                    return None, retry_tokens
                # 재시도: 에러 피드백
                retry_msgs = messages + [
                    {"role": "assistant", "content": response},
                    {"role": "user", "content": f"위 DSL에 에러가 있습니다: {e}\n수정된 DSL을 ```dsl 블록으로 다시 작성해주세요."},
                ]
                try:
                    retry_resp = client.messages.create(
                        model=model, max_tokens=1024, system=system, messages=retry_msgs,
                    )
                    retry_tokens["input"] += retry_resp.usage.input_tokens
                    retry_tokens["output"] += retry_resp.usage.output_tokens
                    new_dsl = self._extract_dsl(retry_resp.content[0].text)
                    if new_dsl:
                        dsl = new_dsl
                        response = retry_resp.content[0].text
                except Exception:
                    return None, retry_tokens
        return None, retry_tokens

    # ── 대화 관리 ──

    def list_conversations(self, user_id: str) -> list[dict]:
        """사용자의 대화 목록."""
        rows = self.db.query(AIConversation).filter(
            AIConversation.user_id == user_id,
        ).order_by(AIConversation.updated_at.desc()).all()
        return [
            {"id": r.id, "title": r.title, "mode": r.mode,
             "strategy_id": r.strategy_id, "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]

    def get_conversation(self, conv_id: str, user_id: str) -> dict | None:
        """대화 상세."""
        r = self.db.query(AIConversation).filter(
            AIConversation.id == conv_id, AIConversation.user_id == user_id,
        ).first()
        if not r:
            return None
        return {
            "id": r.id, "title": r.title, "mode": r.mode,
            "strategy_id": r.strategy_id, "messages": r.messages,
            "current_dsl": r.current_dsl, "updated_at": r.updated_at.isoformat(),
        }

    def delete_conversation(self, conv_id: str, user_id: str) -> bool:
        """대화 삭제."""
        r = self.db.query(AIConversation).filter(
            AIConversation.id == conv_id, AIConversation.user_id == user_id,
        ).first()
        if not r:
            return False
        self.db.delete(r)
        self.db.commit()
        return True
