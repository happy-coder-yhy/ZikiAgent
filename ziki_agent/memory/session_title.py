from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("session_title")

TITLE_SYSTEM_PROMPT = """你是会话标题生成器。根据对话内容生成简短的标题。

【规则】
- 标题不超过 15 个字
- 只输出标题文本，不要加引号、标点或任何解释
- 如果对话内容不足以生成有意义的标题（如纯寒暄、单字），输出"新对话"
- 标题应概括对话的核心主题或用户意图"""


class SessionTitleManager:
    """Calls an LLM to generate a short session title from the first turn.

    Created once per Agent, shared across sessions.  Has its own
    ThreadPoolExecutor for isolated async execution.
    """

    def __init__(self) -> None:
        # Resolve provider & model — same pattern as core.py Agent
        provider = os.environ.get("ZIKI_PROVIDER")
        model = os.environ.get("ZIKI_LLM_MODEL")
        if not provider or not model:
            try:
                from hermes_cli.config import load_config
                cfg = load_config()
                provider = provider or cfg.get("model", {}).get("provider", "deepseek")
                model = model or cfg.get("model", {}).get("default", "deepseek-v4-flash")
            except Exception:
                pass
        provider = provider or "deepseek"
        model = model or "deepseek-v4-flash"

        from run_agent import AIAgent
        self._agent = AIAgent(
            provider=provider,
            model=model,
            quiet_mode=True,
            ephemeral_system_prompt=TITLE_SYSTEM_PROMPT,
        )
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def generate_title(
        self, user_message: str, assistant_response: str,
    ) -> str:
        """Generate a short title from the first turn of conversation.

        Args:
            user_message: the user's first message.
            assistant_response: the assistant's final text response.

        Returns:
            A title string (≤15 chars), or "新对话" on failure.
        """
        # Build a compact prompt — just the dialogue
        user_prompt = (
            f"用户：{user_message}\n"
            f"助手：{assistant_response}\n\n"
            f"请为这段对话生成标题："
        )

        import sys
        try:
            loop = asyncio.get_running_loop()
            raw_result = await loop.run_in_executor(
                self._executor,
                lambda: self._agent.run_conversation(
                    user_message=user_prompt,
                    conversation_history=None,
                ),
            )

            title = (raw_result.get("final_response") or "").strip()
            # Strip common wrapping characters the LLM might add
            for ch in ('"', "'", "「", "」", "《", "》", "【", "】"):
                title = title.strip(ch)
            title = title.strip()

            if not title:
                return "新对话"

            # Reject garbage titles (error messages, etc.)
            _GARBAGE_PATTERNS = [
                "api call failed", "error", "failed", "retry",
                "sorry", "i cannot", "i can't", "unable",
            ]
            title_lower = title.lower()
            if any(p in title_lower for p in _GARBAGE_PATTERNS):
                logger.warning("Rejected garbage title: %s", title)
                return "新对话"

            # Enforce 15-char limit (Chinese chars ≈ 1 word each)
            if len(title) > 15:
                title = title[:15]

            print(
                f"[session-title] Generated: \"{title}\"",
                file=sys.stderr, flush=True,
            )
            return title

        except Exception:
            logger.exception("Session title generation failed")
            return "新对话"

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
        if hasattr(self._agent, "close"):
            self._agent.close()
