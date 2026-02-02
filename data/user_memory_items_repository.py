"""
User Memory Items Repository
Append-only memory items (facts/preferences/plans/notes).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client


class UserMemoryItemsRepository:
    """Repository for `user_memory_items`."""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "user_memory_items"

    def create_item(
        self,
        user_id: int,
        kind: str,
        content: str,
        source: Optional[str] = None,
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        data = {
            "user_id": int(user_id),
            "kind": kind,
            "content": content,
            "source": source,
            "importance": float(importance),
        }
        res = self.client.table(self.table_name).insert(data).execute()
        if res.data:
            return res.data[0]
        raise Exception("Failed to create user_memory_items row")

    def get_recent(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        res = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def keyword_search(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        limit = max(1, min(50, int(limit)))
        # Simple ILIKE search; semantic search will be built on embeddings.
        res = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .ilike("content", f"%{q}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def touch_updated_at(self, memory_item_id: int) -> None:
        try:
            self.client.table(self.table_name).update(
                {"updated_at": datetime.now().isoformat()}
            ).eq("id", int(memory_item_id)).execute()
        except Exception:
            pass

