from __future__ import annotations

from typing import Any

# pyrefly: ignore [missing-import]
from openai import AsyncOpenAI

from ..core.config import get_settings
from ..core.logger import logger


class LLMClientError(Exception):
    """Raised when the groq chat-completion call failes or it not configured"""

    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(message)


class GroqLLMClient:
    """
    Thin async wrapper around Groq's OpenAI-compatible Chat Completions API.

    Groq exposes an OpenAI-compatible endpoint, so the official ``openai`` SDK
    works by pointing it at Groq's base URL. Keeping the rest of the codebase
    free of direct SDK imports means swapping providers later is a config
    change, not a refactor.

    Raises:
        LLMClientError: if GROQ_API_KEY is missing or the API call fails.
        """

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.GROQ_API_KEY:
            raise LLMClientError(
                "AI provider is not configured",
                detail=(
                    "GROQ_API_KEY is missing; cannot instantiate chat client.",
                ),
            )
        self._client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
        )
        self._model = settings.GROQ_MODEL

    @property
    def model(self) -> str:
        return self._model

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 4000,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Perform one chat-completion call and return content + token usage.

        Args:
            messages: OpenAI-style message list (system / user / assistant).
            temperature: low default (0.2) — analysis reports want determinism.
            max_tokens: output cap — guardrail on cost and runaway generations.
            tools: Optional list of tool schemas for function calling.

        Returns:
            dict with keys: content, model, prompt_tokens, completion_tokens, tool_calls.
        """
        logger.info(f"LLM call starting | model={self._model} | messages={len(messages)}")

        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # SDK raises many exception subclasses; unify them
            logger.error(f"LLM call failed: {exc}")
            raise LLMClientError(
                "AI provider call failed",
                detail=str(exc)[:500],
            ) from exc

        choice = response.choices[0] if response.choices else None
        content = ""
        tool_calls = None
        if choice is not None and choice.message is not None:
            content = choice.message.content or ""
            tool_calls = getattr(choice.message, "tool_calls", None)

        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        used_model = getattr(response, "model", self._model) or self._model

        logger.info(
            f"LLM call finished | model={used_model} | "
            f"prompt_tokens={prompt_tokens} | completion_tokens={completion_tokens}"
        )

        return {
            "content": content.strip() if content else "",
            "model": used_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tool_calls": tool_calls,
            "raw_message": choice.message if choice else None,
        }