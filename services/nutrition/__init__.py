"""
Nutrition services (external data sources + caching).
"""

try:
    from .resolver import NutritionResolver
except Exception:  # pragma: no cover
    NutritionResolver = None  # type: ignore[assignment]

__all__ = ["NutritionResolver"]

