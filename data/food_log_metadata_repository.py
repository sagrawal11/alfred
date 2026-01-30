"""
Food Log Metadata Repository
Stores source/confidence metadata for each food log entry.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from supabase import Client

from .base_repository import BaseRepository


class FoodLogMetadataRepository(BaseRepository):
    """Repository for food_log_metadata table."""

    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, "food_log_metadata")

    def create_metadata(
        self,
        *,
        food_log_id: int,
        source: str,
        confidence: float = 0.5,
        basis: Optional[str] = None,
        serving_weight_grams: Optional[float] = None,
        resolved_name: Optional[str] = None,
        raw_query: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not food_log_id or not source:
            return None
        data: Dict[str, Any] = {
            "food_log_id": int(food_log_id),
            "source": str(source),
            "confidence": float(confidence),
            "basis": basis,
            "serving_weight_grams": serving_weight_grams,
            "resolved_name": resolved_name,
            "raw_query": raw_query,
            "raw": raw,
        }
        try:
            return self.create(data)
        except Exception:
            return None

