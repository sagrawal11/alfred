"""
Nutrition types and shared helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class NutritionResult:
    calories: Optional[float]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    source: str
    confidence: float = 0.5
    basis: str = "serving"  # 'serving' | '100g'
    serving_weight_grams: Optional[float] = None
    resolved_name: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def to_parser_fields(self) -> Dict[str, Any]:
        """Shape compatible with Parser/FoodHandler dicts."""
        return {
            "calories": self.calories,
            "protein": self.protein_g,
            "carbs": self.carbs_g,
            "fat": self.fat_g,
            "nutrition_source": self.source,
            "nutrition_confidence": self.confidence,
            "nutrition_basis": self.basis,
            "serving_weight_grams": self.serving_weight_grams,
            "resolved_name": self.resolved_name,
            "nutrition_raw": self.raw,
        }

