"""
LLM Client Types
Defines a provider-agnostic interface for NLP components.
"""

from __future__ import annotations

from typing import Optional, Protocol


class LLMClient(Protocol):
    def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        is_retry: bool = False,
    ) -> str:
        ...

