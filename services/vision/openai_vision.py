"""
OpenAI Vision helper (Responses API).
Used for dashboard image analysis (labels/receipts).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional


class OpenAIVisionClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for vision")

        self.model = (model or os.getenv("OPENAI_VISION_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(text, str):
            return None
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    def analyze_food_image(self, *, image_url: str, kind_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns a structured JSON payload describing either:
        - nutrition label: macros per serving + serving count consumed if inferable
        - receipt/menu screenshot: list of items + quantities
        """
        hint = (kind_hint or "").strip().lower()
        if hint not in ("label", "receipt", "plated", "unknown", ""):
            hint = ""

        instructions = (
            "You are an expert at extracting nutrition info from images.\n"
            "Return ONLY valid JSON. No prose.\n"
            "Privacy rules: do NOT output any addresses, emails, phone numbers, names, card details, or order IDs. "
            "For receipts, output ONLY merchant name (if visible) and item names + quantities.\n"
            "If the image is a Nutrition Facts label, output type='label'.\n"
            "If the image is a receipt or order confirmation, output type='receipt'.\n"
            "If unsure, output type='unknown'.\n"
        )

        prompt = f"""Analyze this image for food logging.

kind_hint: {hint or "none"}

Return JSON in ONE of these schemas:

1) Label:
{{
  "type": "label",
  "product_name": "string|null",
  "servings_consumed": number|null,
  "serving_size_text": "string|null",
  "serving_weight_grams": number|null,
  "per_serving": {{
    "calories": number|null,
    "protein_g": number|null,
    "carbs_g": number|null,
    "fat_g": number|null
  }},
  "confidence": number
}}

2) Receipt / order:
{{
  "type": "receipt",
  "merchant": "string|null",
  "items": [
    {{"name": "string", "quantity": number|null}}
  ],
  "confidence": number
}}

3) Unknown:
{{ "type": "unknown", "confidence": number }}
"""

        resp = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
        )

        text = getattr(resp, "output_text", "") or ""
        parsed = self._extract_json(text)
        if not parsed:
            return {"type": "unknown", "confidence": 0.0, "raw_text": text}
        return parsed

