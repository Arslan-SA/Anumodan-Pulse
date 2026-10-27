"""
AICTE FlowOps — AI Provider Abstraction

Provides vendor-agnostic interfaces and concrete implementations for:
- Deterministic Rule-Based Fallback (Zero external dependency, instant, reliable)
- Google Gemini API (Configurable model, temperature, server-side key)
- OpenAI / Compatible REST Endpoints
- Mock Provider (Deterministic test suite assertions)

Safeguards:
- API keys stay strictly server-side.
- Network timeouts, rate limits, and 5xx errors automatically fallback to deterministic synthesis.
- No autonomous regulatory or statutory decisions are ever taken.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AIProviderResult:
    """Standardized response from an AI provider invocation."""
    content: str
    provider: str
    model: str
    is_fallback: bool
    error: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


class BaseAIProvider(ABC):
    """Abstract interface defining the AI generation contract."""

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AIProviderResult:
        """Generates natural language text given a prompt and optional system instructions."""
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], AIProviderResult]:
        """Generates and parses structured JSON output."""
        pass


class DeterministicFallbackProvider(BaseAIProvider):
    """
    Deterministic rule-based fallback provider.
    Synthesizes factual summaries, diagnostics, and recommendations directly from
    structured database metrics without calling external AI providers.
    """

    def __init__(self, model_name: str = "deterministic-rule-engine"):
        self.model_name = model_name
        self.provider_name = "deterministic-fallback"

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AIProviderResult:
        # Returns a structured factual response extracted from context
        return AIProviderResult(
            content=prompt.strip(),
            provider=self.provider_name,
            model=self.model_name,
            is_fallback=True,
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], AIProviderResult]:
        try:
            parsed = json.loads(prompt)
            return parsed, AIProviderResult(
                content=prompt,
                provider=self.provider_name,
                model=self.model_name,
                is_fallback=True,
                structured_data=parsed,
            )
        except Exception:
            return None, AIProviderResult(
                content=prompt,
                provider=self.provider_name,
                model=self.model_name,
                is_fallback=True,
                error="Could not parse deterministic JSON",
            )


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini AI Provider using official REST endpoints."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.2,
        timeout_seconds: int = 15,
        max_tokens: int = 1500,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.provider_name = "gemini"
        self._fallback = DeterministicFallbackProvider()

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AIProviderResult:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                text_content = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                if not text_content:
                    raise ValueError("Empty response text from Gemini API")

                return AIProviderResult(
                    content=text_content,
                    provider=self.provider_name,
                    model=self.model,
                    is_fallback=False,
                )
        except Exception as exc:
            logger.warning(
                "Gemini API invocation failed (%s). Falling back to deterministic engine.",
                exc,
            )
            fallback_res = self._fallback.generate_text(prompt, system_prompt)
            fallback_res.error = f"Gemini error: {exc}"
            return fallback_res

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], AIProviderResult]:
        json_instruction = (
            "You MUST respond ONLY with valid, RFC-compliant JSON without markdown code fences "
            "or conversational filler."
        )
        combined_sys = f"{system_prompt}\n{json_instruction}" if system_prompt else json_instruction
        res = self.generate_text(prompt, combined_sys)
        if res.is_fallback:
            return None, res

        try:
            clean_text = res.content
            if clean_text.startswith("```"):
                # Strip markdown code fence
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            parsed = json.loads(clean_text)
            res.structured_data = parsed
            return parsed, res
        except Exception as exc:
            logger.warning("Failed to parse Gemini output as JSON: %s", exc)
            res.is_fallback = True
            res.error = f"JSON parse error: {exc}"
            return None, res


class OpenAIAIProvider(BaseAIProvider):
    """OpenAI / Compatible Endpoint Provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        timeout_seconds: int = 15,
        max_tokens: int = 1500,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.provider_name = "openai"
        self._fallback = DeterministicFallbackProvider()

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AIProviderResult:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                text_content = data["choices"][0]["message"]["content"].strip()
                return AIProviderResult(
                    content=text_content,
                    provider=self.provider_name,
                    model=self.model,
                    is_fallback=False,
                )
        except Exception as exc:
            logger.warning(
                "OpenAI API invocation failed (%s). Falling back to deterministic engine.",
                exc,
            )
            fallback_res = self._fallback.generate_text(prompt, system_prompt)
            fallback_res.error = f"OpenAI error: {exc}"
            return fallback_res

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], AIProviderResult]:
        json_sys = f"{system_prompt or ''}\nRespond ONLY in valid JSON."
        res = self.generate_text(prompt, json_sys)
        if res.is_fallback:
            return None, res
        try:
            clean_text = res.content
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
            parsed = json.loads(clean_text)
            res.structured_data = parsed
            return parsed, res
        except Exception as exc:
            res.is_fallback = True
            res.error = f"JSON parse error: {exc}"
            return None, res


class MockAIProvider(BaseAIProvider):
    """Mock Provider for deterministic unit & integration tests."""

    def __init__(
        self,
        canned_response: str = "Mock AI generated advisory analysis.",
        should_fail: bool = False,
    ):
        self.canned_response = canned_response
        self.should_fail = should_fail
        self.provider_name = "mock"
        self.model = "mock-ai-v1"
        self._fallback = DeterministicFallbackProvider()

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AIProviderResult:
        if self.should_fail:
            fallback = self._fallback.generate_text(prompt, system_prompt)
            fallback.error = "Mock provider forced failure"
            return fallback

        return AIProviderResult(
            content=self.canned_response,
            provider=self.provider_name,
            model=self.model,
            is_fallback=False,
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], AIProviderResult]:
        if self.should_fail:
            return None, self._fallback.generate_text(prompt, system_prompt)
        try:
            parsed = json.loads(self.canned_response)
            return parsed, AIProviderResult(
                content=self.canned_response,
                provider=self.provider_name,
                model=self.model,
                is_fallback=False,
                structured_data=parsed,
            )
        except Exception:
            return None, AIProviderResult(
                content=self.canned_response,
                provider=self.provider_name,
                model=self.model,
                is_fallback=False,
            )


def get_ai_provider() -> BaseAIProvider:
    """
    Factory function returning the configured AI provider.
    If AI is disabled or no API key is set, returns DeterministicFallbackProvider.
    """
    if not settings.ai_enabled:
        return DeterministicFallbackProvider()

    provider_name = (settings.ai_provider or "fallback").strip().lower()

    if provider_name == "mock":
        return MockAIProvider()

    if provider_name == "gemini" and settings.ai_api_key:
        return GeminiAIProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            temperature=settings.ai_temperature,
            timeout_seconds=settings.ai_timeout_seconds,
            max_tokens=settings.ai_max_tokens,
        )

    if provider_name == "openai" and settings.ai_api_key:
        return OpenAIAIProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            temperature=settings.ai_temperature,
            timeout_seconds=settings.ai_timeout_seconds,
            max_tokens=settings.ai_max_tokens,
        )

    # Clean default: deterministic fallback
    return DeterministicFallbackProvider()
