"""
Nutrition Resolver
Tiered lookup across multiple nutrition sources with caching.
"""

from __future__ import annotations

import os
from typing import Optional

from supabase import Client

from data import NutritionCacheRepository

from .providers import NutritionProvider, build_default_providers
from .types import NutritionResult
from .utils import normalize_query, normalize_restaurant


class NutritionResolver:
    """
    Resolves nutrition for a query via:
    - Cache
    - Providers (in configured order)
    - Cache write-back

    Default provider ordering:
    - USDA (if configured)
    - Open Food Facts
    - Nutritionix (if configured)

    Note: if a restaurant is specified (and local DB didn't match), we bias toward Nutritionix first
    since it's more likely to have menu-like items. That still respects caching per provider.
    """

    def __init__(
        self,
        supabase: Client,
        *,
        ttl_days: Optional[int] = None,
        providers: Optional[list[NutritionProvider]] = None,
    ):
        self.cache_repo = NutritionCacheRepository(supabase)
        self.ttl_days = int(ttl_days if ttl_days is not None else int(os.getenv("NUTRITION_CACHE_TTL_DAYS", "30")))
        self.providers = providers or build_default_providers()

    def _provider_order(self, restaurant: Optional[str]) -> list[NutritionProvider]:
        if not restaurant:
            return list(self.providers)

        # Bias: try nutritionix earlier for restaurant/menu-style queries if present.
        nix = [p for p in self.providers if getattr(p, "source", "") == "nutritionix"]
        rest = [p for p in self.providers if getattr(p, "source", "") != "nutritionix"]
        return nix + rest

    def resolve(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        qn = normalize_query(query)
        rn = normalize_restaurant(restaurant)
        if not qn:
            return None

        for provider in self._provider_order(rn):
            source = getattr(provider, "source", "").strip().lower()
            if not source:
                continue

            cached = self.cache_repo.get_cached(qn, rn, source)
            if cached:
                return NutritionResult(
                    calories=cached.get("calories"),
                    protein_g=cached.get("protein"),
                    carbs_g=cached.get("carbs"),
                    fat_g=cached.get("fat"),
                    source=source,
                    confidence=float(cached.get("confidence") or 0.5),
                    basis=str(cached.get("basis") or "serving"),
                    serving_weight_grams=cached.get("serving_weight_grams"),
                    resolved_name=cached.get("resolved_name"),
                    raw=cached.get("raw"),
                )

            result = provider.lookup(query=qn, restaurant=rn)
            if result:
                self.cache_repo.upsert_cached(
                    query=qn,
                    restaurant=rn,
                    source=result.source,
                    calories=result.calories,
                    protein=result.protein_g,
                    carbs=result.carbs_g,
                    fat=result.fat_g,
                    confidence=result.confidence,
                    basis=result.basis,
                    serving_weight_grams=result.serving_weight_grams,
                    resolved_name=result.resolved_name,
                    raw=result.raw,
                    ttl_days=self.ttl_days,
                )
                return result

        return None

