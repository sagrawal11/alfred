"""
User Usage Repository
Tracks monthly agent \"turn\" usage for quota enforcement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client


class UserUsageRepository:
    """Repository for user_usage_monthly (PK = (user_id, month_key))."""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "user_usage_monthly"

    @staticmethod
    def month_key_for(dt: Optional[datetime] = None) -> str:
        d = dt or datetime.utcnow()
        return f"{d.year:04d}-{d.month:02d}"

    def get_month(self, user_id: int, month_key: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .eq("month_key", str(month_key))
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None

    def increment_month(self, user_id: int, month_key: str, delta: int = 1) -> int:
        # Prefer RPC for atomic increment if available
        try:
            res = self.client.rpc(
                "increment_user_usage_monthly",
                {"p_user_id": int(user_id), "p_month_key": str(month_key), "p_delta": int(delta)},
            ).execute()
            # Supabase RPC returns data; for scalar returns, it may be a list or a value depending on client.
            if isinstance(res.data, list) and res.data:
                return int(res.data[0])
            if res.data is not None:
                return int(res.data)
        except Exception:
            pass

        # Fallback: read then update (non-atomic)
        row = self.get_month(int(user_id), month_key)
        if not row:
            ins = self.client.table(self.table_name).insert(
                {"user_id": int(user_id), "month_key": str(month_key), "turns_used": max(0, int(delta))}
            ).execute()
            if ins.data:
                return int(ins.data[0].get("turns_used") or 0)
            return max(0, int(delta))

        turns = int(row.get("turns_used") or 0) + max(0, int(delta))
        upd = (
            self.client.table(self.table_name)
            .update({"turns_used": turns, "updated_at": datetime.utcnow().isoformat()})
            .eq("user_id", int(user_id))
            .eq("month_key", str(month_key))
            .execute()
        )
        if upd.data:
            return int(upd.data[0].get("turns_used") or turns)
        return turns

