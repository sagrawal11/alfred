"""
Food Image Upload Repository
Tracks uploaded food-related images (labels, receipts, plated food) for dashboard processing.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from supabase import Client

from .base_repository import BaseRepository


class FoodImageUploadRepository(BaseRepository):
    """Repository for food_image_uploads table."""

    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, "food_image_uploads")

    def create_upload(
        self,
        *,
        user_id: int,
        bucket: str,
        path: str,
        mime_type: str,
        size_bytes: int,
        status: str = "uploaded",
        kind: Optional[str] = None,  # 'label'|'receipt'|'plated'|'unknown'
        original_filename: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not user_id or not bucket or not path:
            return None
        data: Dict[str, Any] = {
            "user_id": int(user_id),
            "bucket": str(bucket),
            "path": str(path),
            "mime_type": str(mime_type or ""),
            "size_bytes": int(size_bytes or 0),
            "status": str(status),
            "kind": kind,
            "original_filename": original_filename,
        }
        try:
            return self.create(data)
        except Exception:
            return None

