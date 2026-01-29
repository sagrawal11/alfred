"""
OpenAI API Client
Primary LLM provider for NLP (intent classification, entity extraction, parsing).
"""

from __future__ import annotations

import os
import time
from typing import Optional


class OpenAIClient:
    """Client for OpenAI API with basic retry behavior."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        # Lazy import to avoid import-time failures when OpenAI isn't installed
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        is_retry: bool = False,
    ) -> str:
        """
        Generate text using OpenAI.
        Uses Responses API for a simple text-in/text-out flow.
        """
        # Basic backoff on retryable failures
        max_attempts = 2 if not is_retry else 1
        last_err: Optional[Exception] = None

        for attempt in range(max_attempts):
            try:
                if system_prompt:
                    response = self.client.responses.create(
                        model=self.model_name,
                        instructions=system_prompt,
                        input=prompt,
                    )
                else:
                    response = self.client.responses.create(
                        model=self.model_name,
                        input=prompt,
                    )

                # openai SDK provides output_text convenience
                text = getattr(response, "output_text", None)
                if isinstance(text, str):
                    return text.strip()

                # Fallback extraction
                try:
                    out = response.output  # type: ignore[attr-defined]
                    if out:
                        parts = []
                        for item in out:
                            for c in getattr(item, "content", []) or []:
                                t = getattr(c, "text", None)
                                if t:
                                    parts.append(t)
                        return "\n".join(parts).strip()
                except Exception:
                    pass

                return ""
            except Exception as e:
                last_err = e
                # small backoff then retry once
                if attempt < max_attempts - 1:
                    time.sleep(1.0)
                    continue
                break

        if last_err:
            raise last_err
        return ""

