"""
User Preferences Repository
Stores per-user settings in user_preferences (PK = user_id)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client


class UserPreferencesRepository:
    """Repository for per-user preferences (user_preferences table)"""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "user_preferences"

    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    def ensure(self, user_id: int) -> Dict[str, Any]:
        """Ensure a preference row exists for user_id and return it."""
        existing = self.get(user_id)
        if existing:
            return existing

        result = self.client.table(self.table_name).insert({"user_id": user_id}).execute()
        if result.data:
            return result.data[0]
        # In rare cases, insert may race; try one more read
        existing = self.get(user_id)
        if existing:
            return existing
        raise Exception("Failed to ensure user_preferences row")

    def update(self, user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update preferences for user_id (PK), returning updated row if available."""
        if "updated_at" not in data:
            data["updated_at"] = datetime.now().isoformat()

        result = (
            self.client.table(self.table_name)
            .update(data)
            .eq("user_id", user_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

