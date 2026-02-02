"""
User Memory State Repository
Stores per-user running summary + style profile (PK = user_id).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client


class UserMemoryStateRepository:
    """Repository for `user_memory_state` (PK = user_id)."""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "user_memory_state"

    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None

    def ensure(self, user_id: int) -> Dict[str, Any]:
        existing = self.get(user_id)
        if existing:
            return existing
        res = self.client.table(self.table_name).insert({"user_id": user_id}).execute()
        if res.data:
            return res.data[0]
        existing = self.get(user_id)
        if existing:
            return existing
        raise Exception("Failed to ensure user_memory_state row")

    def update(self, user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "updated_at" not in data:
            data["updated_at"] = datetime.now().isoformat()
        res = (
            self.client.table(self.table_name)
            .update(data)
            .eq("user_id", user_id)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None

