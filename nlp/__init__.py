"""
NLP Layer
Modular NLP processing components
"""

try:
    # Gemini is optional; on older Python versions or missing deps,
    # importing Google libs can fail. Keep the package importable so
    # OpenAI-only deployments still run.
    from .gemini_client import GeminiClient  # type: ignore
except Exception:  # pragma: no cover
    GeminiClient = None  # type: ignore
from .llm_client import create_llm_client
from .llm_types import LLMClient
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .parser import Parser
from .pattern_matcher import PatternMatcher
from .database_loader import DatabaseLoader

__all__ = [
    'LLMClient',
    'create_llm_client',
    'GeminiClient',
    'IntentClassifier',
    'EntityExtractor',
    'Parser',
    'PatternMatcher',
    'DatabaseLoader',
]
