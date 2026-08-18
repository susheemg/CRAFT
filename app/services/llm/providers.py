"""Provider adapters.

Each adapter turns one neutral :class:`ChatRequest` into a provider-specific
HTTP call and returns a neutral :class:`ChatResponse`. Nothing above this layer
knows which vendor served a request, which is what makes the platform
model-agnostic and lets an administrator swap providers from the console.

Prompt caching is handled per provider, because the mechanisms differ:

  * **Anthropic** — explicit ``cache_control: {"type": "ephemeral"}`` breakpoints.
    The adapter marks the end of the stable system prefix, so the standards
    text and control catalogue in front of every assessment prompt is written
    to cache once and read cheaply thereafter.
  * **OpenAI / Azure** — automatic prefix caching for long prompts. There is no
    flag to set; the adapter's job is to keep the prefix stable and first,
    and to read the ``cached_tokens`` the API reports back.
  * **Bedrock / Google / others** — treated as no native cache. The platform's
    own exact-match cache still applies, so these providers are not penalised.

Adding a provider means adding one subclass and one entry in ``ADAPTERS``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """A provider call failed. ``retryable`` drives the fallback decision."""

    def __init__(self, message: str, *, status: int | None = None, retryable: bool = True):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


@dataclass
class ChatRequest:
    """Neutral request. ``cache_prefix`` is the stable head of the system prompt."""

    prompt: str
    system: str = ""
    cache_prefix: str = ""
    max_tokens: int = 2048
    temperature: float = 0.0
    json_mode: bool = False
    stop: list[str] = field(default_factory=list)

    @property
    def full_system(self) -> str:
        parts = [p for p in (self.cache_prefix, self.system) if p]
        return "\n\n".join(parts)


@dataclass
class ChatResponse:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str = ""
    raw_finish_reason: str = ""

    @property
    def provider_cache_hit(self) -> bool:
        return self.cache_read_tokens > 0


class BaseAdapter:
    kind = "base"
    supports_native_cache = False
    # Below this many characters, provider-side caching is not worth a breakpoint.
    MIN_CACHEABLE_PREFIX_CHARS = 2000

    def __init__(
        self,
        api_key: str,
        model_key: str,
        base_url: str | None = None,
        region: str | None = None,
        api_version: str | None = None,
        extra_headers: dict | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.model_key = model_key
        self.base_url = (base_url or self.default_base_url()).rstrip("/")
        self.region = region
        self.api_version = api_version
        self.extra_headers = extra_headers or {}
        self.timeout = timeout

    def default_base_url(self) -> str:
        raise NotImplementedError

    async def chat(self, req: ChatRequest, client: httpx.AsyncClient) -> ChatResponse:
        raise NotImplementedError

    async def health(self, client: httpx.AsyncClient) -> tuple[bool, str]:
        """Server-side connectivity probe. Never returns credential material."""
        try:
            resp = await self.chat(
                ChatRequest(prompt="Reply with the single word: ok", max_tokens=8),
                client,
            )
            return True, f"Reachable. Model replied in {len(resp.text)} characters."
        except ProviderError as exc:
            return False, str(exc)[:400]
        except Exception as exc:  # noqa: BLE001 - surfaced to the admin console
            return False, f"{type(exc).__name__}: {str(exc)[:300]}"

    @staticmethod
    def _raise_for_status(resp: httpx.Response, vendor: str) -> None:
        if resp.status_code < 400:
            return
        # 4xx other than 408/429 will not succeed on retry; do not burn the chain.
        retryable = resp.status_code in (408, 409, 429) or resp.status_code >= 500
        try:
            detail = resp.json().get("error", {})
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
        except (ValueError, AttributeError):
            message = resp.text[:300]
        raise ProviderError(
            f"{vendor} returned {resp.status_code}: {message}",
            status=resp.status_code,
            retryable=retryable,
        )


class AnthropicAdapter(BaseAdapter):
    kind = "anthropic"
    supports_native_cache = True

    def default_base_url(self) -> str:
        return "https://api.anthropic.com"

    async def chat(self, req: ChatRequest, client: httpx.AsyncClient) -> ChatResponse:
        system_blocks: list[dict[str, Any]] = []
        if req.cache_prefix:
            block: dict[str, Any] = {"type": "text", "text": req.cache_prefix}
            if len(req.cache_prefix) >= self.MIN_CACHEABLE_PREFIX_CHARS:
                # The breakpoint tells the provider where the reusable prefix ends.
                block["cache_control"] = {"type": "ephemeral"}
            system_blocks.append(block)
        if req.system:
            system_blocks.append({"type": "text", "text": req.system})

        body: dict[str, Any] = {
            "model": self.model_key,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if system_blocks:
            body["system"] = system_blocks
        if req.stop:
            body["stop_sequences"] = req.stop

        resp = await client.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.api_version or "2023-06-01",
                "content-type": "application/json",
                **self.extra_headers,
            },
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(resp, "Anthropic")
        data = resp.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        return ChatResponse(
            text=text,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            cache_write_tokens=usage.get("cache_creation_input_tokens", 0),
            model=data.get("model", self.model_key),
            raw_finish_reason=data.get("stop_reason", ""),
        )


class OpenAiAdapter(BaseAdapter):
    """OpenAI and anything that speaks its chat-completions dialect."""

    kind = "openai"
    supports_native_cache = True

    def default_base_url(self) -> str:
        return "https://api.openai.com"

    def _url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

    def _body(self, req: ChatRequest) -> dict:
        messages = []
        if req.full_system:
            # Prefix first and unchanged between calls: that is what makes the
            # provider's automatic prefix cache actually hit.
            messages.append({"role": "system", "content": req.full_system})
        messages.append({"role": "user", "content": req.prompt})
        body: dict[str, Any] = {
            "model": self.model_key,
            "messages": messages,
            "max_completion_tokens": req.max_tokens,
        }
        if req.temperature is not None:
            body["temperature"] = req.temperature
        if req.json_mode:
            body["response_format"] = {"type": "json_object"}
        if req.stop:
            body["stop"] = req.stop
        return body

    async def chat(self, req: ChatRequest, client: httpx.AsyncClient) -> ChatResponse:
        resp = await client.post(
            self._url(), headers=self._headers(), json=self._body(req), timeout=self.timeout
        )
        self._raise_for_status(resp, "OpenAI")
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage", {})
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        return ChatResponse(
            text=(choice.get("message") or {}).get("content", "") or "",
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            cache_read_tokens=cached,
            model=data.get("model", self.model_key),
            raw_finish_reason=choice.get("finish_reason", ""),
        )


class AzureOpenAiAdapter(OpenAiAdapter):
    kind = "azure_openai"

    def default_base_url(self) -> str:
        raise ProviderError(
            "Azure OpenAI requires the resource endpoint as the base URL, "
            "e.g. https://my-resource.openai.azure.com",
            retryable=False,
        )

    def _url(self) -> str:
        version = self.api_version or "2024-10-21"
        return f"{self.base_url}/openai/deployments/{self.model_key}/chat/completions?api-version={version}"

    def _headers(self) -> dict:
        return {"api-key": self.api_key, "Content-Type": "application/json", **self.extra_headers}


class OpenAiCompatibleAdapter(OpenAiAdapter):
    """Together, Groq, Fireworks, vLLM, LiteLLM proxies and similar."""

    kind = "openai_compatible"
    supports_native_cache = False

    def default_base_url(self) -> str:
        raise ProviderError(
            "An OpenAI-compatible provider needs an explicit base URL.", retryable=False
        )


class OllamaAdapter(OpenAiAdapter):
    """Self-hosted models. No API key required."""

    kind = "ollama"
    supports_native_cache = False

    def default_base_url(self) -> str:
        return "http://localhost:11434"

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", **self.extra_headers}


class GoogleAdapter(BaseAdapter):
    kind = "google"

    def default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com"

    async def chat(self, req: ChatRequest, client: httpx.AsyncClient) -> ChatResponse:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": req.prompt}]}],
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        if req.full_system:
            body["systemInstruction"] = {"parts": [{"text": req.full_system}]}
        resp = await client.post(
            f"{self.base_url}/v1beta/models/{self.model_key}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json",
                     **self.extra_headers},
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(resp, "Google")
        data = resp.json()
        candidates = data.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        usage = data.get("usageMetadata", {})
        return ChatResponse(
            text="".join(p.get("text", "") for p in parts),
            tokens_in=usage.get("promptTokenCount", 0),
            tokens_out=usage.get("candidatesTokenCount", 0),
            cache_read_tokens=usage.get("cachedContentTokenCount", 0),
            model=self.model_key,
            raw_finish_reason=candidates[0].get("finishReason", ""),
        )


class BedrockAdapter(BaseAdapter):
    """Amazon Bedrock via an SigV4-signing gateway or proxy.

    Direct SigV4 signing is intentionally out of scope for the single-service
    deployment: it needs the AWS SDK and an instance role. Point ``base_url`` at
    a Bedrock access gateway that accepts an Anthropic-shaped payload, which is
    the common enterprise pattern, and this adapter works unchanged.
    """

    kind = "bedrock"

    def default_base_url(self) -> str:
        raise ProviderError(
            "Bedrock requires a base URL pointing at your Bedrock access gateway.",
            retryable=False,
        )

    async def chat(self, req: ChatRequest, client: httpx.AsyncClient) -> ChatResponse:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if req.full_system:
            body["system"] = req.full_system
        resp = await client.post(
            f"{self.base_url}/model/{self.model_key}/invoke",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json", **self.extra_headers},
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(resp, "Bedrock")
        data = resp.json()
        if isinstance(data, str):
            data = json.loads(data)
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        usage = data.get("usage", {})
        return ChatResponse(
            text=text,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            model=self.model_key,
        )


ADAPTERS: dict[str, type[BaseAdapter]] = {
    "anthropic": AnthropicAdapter,
    "openai": OpenAiAdapter,
    "azure_openai": AzureOpenAiAdapter,
    "openai_compatible": OpenAiCompatibleAdapter,
    "ollama": OllamaAdapter,
    "google": GoogleAdapter,
    "bedrock": BedrockAdapter,
}

PROVIDER_KINDS = tuple(ADAPTERS.keys())


def build_adapter(kind: str, **kwargs) -> BaseAdapter:
    try:
        return ADAPTERS[kind](**kwargs)
    except KeyError as exc:
        raise ProviderError(
            f"Unknown provider kind '{kind}'. Supported: {', '.join(PROVIDER_KINDS)}",
            retryable=False,
        ) from exc
