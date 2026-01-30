"""
Nutrition Cache Repository
Caches resolved nutrition lookups to reduce external API calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from supabase import Client

from .base_repository import BaseRepository


class NutritionCacheRepository(BaseRepository):
    """Repository for nutrition_cache table."""

    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, "nutrition_cache")

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    def get_cached(self, query: str, restaurant: Optional[str], source: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a cached entry if present and not expired.
        """
        q = (query or "").strip().lower()
        r = (restaurant or "").strip().lower() or None
        s = (source or "").strip().lower()
        if not q or not s:
            return None

        req = self.client.table(self.table_name).select("*").eq("query", q).eq("source", s)
        if r is None:
            req = req.is_("restaurant", "null")
        else:
            req = req.eq("restaurant", r)

        res = req.order("cached_at", desc=True).limit(1).execute()
        if not res.data:
            return None

        row = res.data[0]
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                # Supabase returns ISO strings
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if exp <= self._now_utc():
                    return None
            except Exception:
                # If expires_at can't be parsed, treat as expired to be safe
                return None
        return row

    def upsert_cached(
        self,
        *,
        query: str,
        restaurant: Optional[str],
        source: str,
        calories: Optional[float],
        protein: Optional[float],
        carbs: Optional[float],
        fat: Optional[float],
        confidence: float = 0.5,
        basis: str = "serving",
        serving_weight_grams: Optional[float] = None,
        resolved_name: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
        ttl_days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        q = (query or "").strip().lower()
        r = (restaurant or "").strip().lower() or None
        s = (source or "").strip().lower()
        if not q or not s:
            return None

        now = self._now_utc()
        expires_at = now + timedelta(days=max(int(ttl_days), 1))

        payload: Dict[str, Any] = {
            "query": q,
            "restaurant": r,
            "source": s,
            "resolved_name": resolved_name,
            "basis": basis,
            "serving_weight_grams": serving_weight_grams,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "confidence": float(confidence),
            "raw": raw,
            "cached_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        try:
            # Use PostgREST upsert on unique(query, restaurant, source)
            res = self.client.table(self.table_name).upsert(payload, on_conflict="query,restaurant,source").execute()
            if res.data:
                return res.data[0]
        except Exception:
            # If upsert isn't available or fails, fall back to insert (may duplicate if constraint missing)
            try:
                res = self.client.table(self.table_name).insert(payload).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                return None

        return None

