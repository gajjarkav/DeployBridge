from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from ..core.config import get_settings
from ..core.logger import logger


class LLMClientError(Exception):
    """Raised when the chat-completion call fails or the provider is not configured."""

    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(message)


# ---------------------------------------------------------------------------
# Azure AI Foundry client (primary)
# ---------------------------------------------------------------------------

class AzureLLMClient:
    """
    Async wrapper around Azure AI Foundry's OpenAI-compatible Chat Completions endpoint.

    Authentication priority:
      1. AZURE_AI_API_KEY  — static key from env (simplest, good for local dev)
      2. DefaultAzureCredential — managed-identity / az-login / env-vars
         (used in production / CI where no static key is stored)

    The openai SDK is pointed at the Foundry endpoint with a bearer-token
    callable when using credential-based auth.
    """

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.AZURE_AI_ENDPOINT:
            raise LLMClientError(
                "Azure AI provider is not configured",
                detail="AZURE_AI_ENDPOINT is missing in settings.",
            )

        self._model = settings.AZURE_AI_DEPLOYMENT
        self._api_version = settings.AZURE_AI_API_VERSION

        if settings.AZURE_AI_API_KEY:
            # Static API key — simplest path
            # Note: no api-version needed — the /v1 path is OpenAI-compatible
            self._client = AsyncOpenAI(
                base_url=settings.AZURE_AI_ENDPOINT,
                api_key=settings.AZURE_AI_API_KEY,
                timeout=settings.AZURE_AI_TIMEOUT_SECONDS,
            )
            logger.info(f"AzureLLMClient: using static API key auth | model={self._model}")
        else:
            # Credential-based auth (DefaultAzureCredential)
            try:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider  # type: ignore
            except ImportError as exc:
                raise LLMClientError(
                    "azure-identity is not installed",
                    detail=(
                        "Run: pip install azure-identity\n"
                        "Or set AZURE_AI_API_KEY to use static key auth instead."
                    ),
                ) from exc

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://ai.azure.com/.default"
            )
            self._client = AsyncOpenAI(
                base_url=settings.AZURE_AI_ENDPOINT,
                api_key=token_provider,
                timeout=settings.AZURE_AI_TIMEOUT_SECONDS,
            )
            logger.info(f"AzureLLMClient: using DefaultAzureCredential auth | model={self._model}")

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
        logger.info(f"Azure LLM call | model={self._model} | messages={len(messages)}")

        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
            }
            
            # Newer Azure AI models (o1, gpt-5-mini, etc.) strictly only support temperature=1
            if "gpt-5" not in self._model.lower() and "o1" not in self._model.lower():
                kwargs["temperature"] = temperature
            else:
                kwargs["temperature"] = 1.0
            if tools:
                kwargs["tools"] = tools

            response = await self._client.chat.completions.create(**kwargs)

        except Exception as exc:
            logger.error(f"Azure LLM call failed: {exc}")
            raise LLMClientError("Azure AI call failed", detail=str(exc)[:500]) from exc

        return _parse_response(response, self._model)


# ---------------------------------------------------------------------------
# Gemini (fallback) client — keeps the legacy GroqLLMClient name so callers
# don't need any changes.
# ---------------------------------------------------------------------------

class GeminiLLMClient:
    """
    Thin async wrapper around Google Gemini via its OpenAI-compatible endpoint.
    GROQ_API_KEY is optional — if absent, Gemini fallback is silently skipped.
    """

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.GROQ_API_KEY:
            raise LLMClientError(
                "Gemini fallback is not configured",
                detail="GROQ_API_KEY (Gemini key) is missing.",
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
        logger.info(f"Gemini fallback LLM call | model={self._model} | messages={len(messages)}")

        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools

            response = await self._client.chat.completions.create(**kwargs)

        except Exception as exc:
            logger.error(f"Gemini LLM call failed: {exc}")
            raise LLMClientError("Gemini AI call failed", detail=str(exc)[:500]) from exc

        return _parse_response(response, self._model)


# ---------------------------------------------------------------------------
# GroqLLMClient — backward-compatible alias that tries Azure first, falls
# back to Gemini automatically.  All existing callers work with zero changes.
# ---------------------------------------------------------------------------

class GroqLLMClient:
    """
    Backward-compatible LLM client.

    Resolution order:
      1. Azure AI Foundry GPT-5 mini  (primary)
      2. Gemini via OpenAI-compat endpoint (fallback, only if GROQ_API_KEY set)

    Raises LLMClientError only when BOTH providers are unavailable.
    """

    def __init__(self) -> None:
        self._primary: AzureLLMClient | None = None
        self._fallback: GeminiLLMClient | None = None

        try:
            self._primary = AzureLLMClient()
            logger.info("GroqLLMClient: primary=AzureAI (gpt-5-mini)")
        except LLMClientError as exc:
            logger.warning(f"Azure AI unavailable ({exc.message}), will try Gemini fallback.")

        try:
            self._fallback = GeminiLLMClient()
            logger.info("GroqLLMClient: fallback=Gemini configured")
        except LLMClientError:
            logger.info("GroqLLMClient: Gemini fallback not configured (GROQ_API_KEY absent)")

        if self._primary is None and self._fallback is None:
            raise LLMClientError(
                "No LLM provider is configured",
                detail=(
                    "Set AZURE_AI_ENDPOINT (+ AZURE_AI_API_KEY or DefaultAzureCredential) "
                    "and/or GROQ_API_KEY (Gemini)."
                ),
            )

    @property
    def model(self) -> str:
        active = self._primary or self._fallback
        return active.model if active else "unknown"  # type: ignore[union-attr]

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 4000,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        kwargs = dict(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

        # Try primary (Azure)
        if self._primary is not None:
            try:
                return await self._primary.chat_completion(**kwargs)
            except LLMClientError as exc:
                logger.warning(
                    f"Azure primary failed ({exc.message}); trying Gemini fallback."
                )

        # Try fallback (Gemini)
        if self._fallback is not None:
            return await self._fallback.chat_completion(**kwargs)

        raise LLMClientError(
            "All LLM providers failed",
            detail="Both Azure AI and Gemini are unavailable.",
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _parse_response(response: Any, default_model: str) -> dict[str, Any]:
    choice = response.choices[0] if response.choices else None
    content = ""
    tool_calls = None

    if choice is not None and choice.message is not None:
        content = choice.message.content or ""
        tool_calls = getattr(choice.message, "tool_calls", None)

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    used_model = getattr(response, "model", default_model) or default_model

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