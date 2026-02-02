"""
User Memory Embeddings Repository
Stores one embedding vector per memory item (PK = memory_item_id).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import Client


class UserMemoryEmbeddingsRepository:
    """Repository for `user_memory_embeddings`."""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "user_memory_embeddings"

    def upsert_embedding(self, memory_item_id: int, embedding: List[float], model: str) -> Dict[str, Any]:
        data = {
            "memory_item_id": int(memory_item_id),
            "embedding": embedding,
            "model": model,
        }
        # Upsert is done by inserting; PK conflict behavior depends on PostgREST settings.
        # We’ll try update-first, then insert.
        try:
            res = (
                self.client.table(self.table_name)
                .update({"embedding": embedding, "model": model})
                .eq("memory_item_id", int(memory_item_id))
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception:
            pass

        res = self.client.table(self.table_name).insert(data).execute()
        if res.data:
            return res.data[0]
        raise Exception("Failed to upsert user_memory_embeddings row")

    def get_by_item_ids(self, memory_item_ids: List[int]) -> List[Dict[str, Any]]:
        ids = [int(x) for x in (memory_item_ids or []) if x is not None]
        if not ids:
            return []
        res = (
            self.client.table(self.table_name)
            .select("*")
            .in_("memory_item_id", ids)
            .execute()
        )
        return res.data or []

