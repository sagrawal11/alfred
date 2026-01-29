"""
LLM Client Factory
OpenAI-first with Gemini fallback.
"""

from __future__ import annotations

import os
from typing import Optional

from .llm_types import LLMClient


class HybridLLMClient:
    """OpenAI primary, Gemini fallback on errors/missing key."""

    def __init__(self, openai_client: Optional[LLMClient], gemini_client: Optional[LLMClient]):
        self._openai = openai_client
        self._gemini = gemini_client

    def generate_content(self, prompt: str, system_prompt: Optional[str] = None, is_retry: bool = False) -> str:
        # Prefer OpenAI if present
        if self._openai is not None:
            try:
                return self._openai.generate_content(prompt, system_prompt=system_prompt, is_retry=is_retry)
            except Exception as e:
                # Fall back to Gemini if available
                if self._gemini is not None:
                    print(f"OpenAI failed, falling back to Gemini: {e}")
                    return self._gemini.generate_content(prompt, system_prompt=system_prompt, is_retry=is_retry)
                raise

        # If OpenAI not configured, use Gemini
        if self._gemini is not None:
            return self._gemini.generate_content(prompt, system_prompt=system_prompt, is_retry=is_retry)

        raise ValueError("No LLM provider configured (set OPENAI_API_KEY or GEMINI_API_KEY)")


def create_llm_client() -> LLMClient:
    """
    Create the app's LLM client:
    - OpenAI is default if OPENAI_API_KEY present
    - Gemini is fallback if GEMINI_API_KEY present
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    openai_client = None
    gemini_client = None

    if openai_key:
        from .openai_client import OpenAIClient
        openai_client = OpenAIClient(api_key=openai_key, model_name=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
        print(f"OpenAI client loaded ({os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')})")

    if gemini_key:
        from .gemini_client import GeminiClient
        gemini_client = GeminiClient(api_key=gemini_key, model_name=os.getenv("GEMINI_MODEL"))

    return HybridLLMClient(openai_client=openai_client, gemini_client=gemini_client)

