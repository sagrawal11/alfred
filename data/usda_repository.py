"""
USDA FoodData Central read-only repository.
Queries Supabase tables (usda_food, usda_food_nutrient, usda_nutrient,
usda_food_portion, usda_measure_unit, usda_food_category, usda_branded_food)
for nutrition resolution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import Client

# Standard FDC nutrient IDs for macros
NUTRIENT_ID_ENERGY_KCAL = 1008
NUTRIENT_ID_PROTEIN = 1003
NUTRIENT_ID_CARB = 1005
NUTRIENT_ID_FAT = 1004


def _float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class USDARepository:
    """Read-only access to USDA tables in Supabase."""

    def __init__(self, supabase: Client):
        self.client = supabase

    def search_food(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search usda_food by description (ILIKE). Returns rows with fdc_id, description, etc.
        Ordered by description length for relevance (shorter = often better match).
        """
        q = (query or "").strip()
        if not q:
            return []
        pattern = f"%{q}%"
        try:
            # Supabase/PostgREST: ilike via filter. Order by length(description) to prefer shorter matches.
            r = (
                self.client.table("usda_food")
                .select("fdc_id, description, data_type, food_category_id")
                .ilike("description", pattern)
                .limit(limit * 3)  # fetch more then sort by length in Python (Supabase may not support length order)
                .execute()
            )
        except Exception:
            return []
        rows = r.data or []
        # Prefer shorter description (more specific match)
        rows.sort(key=lambda x: len(str(x.get("description") or "")))
        return rows[:limit]

    def get_macros(self, fdc_id: int) -> Dict[str, Optional[float]]:
        """
        Get calories, protein_g, carbs_g, fat_g for a food by fdc_id.
        Reads from usda_food_nutrient joined to usda_nutrient.
        """
        out = {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None}
        nutrient_ids = [NUTRIENT_ID_ENERGY_KCAL, NUTRIENT_ID_PROTEIN, NUTRIENT_ID_CARB, NUTRIENT_ID_FAT]
        try:
            r = (
                self.client.table("usda_food_nutrient")
                .select("nutrient_id, amount")
                .eq("fdc_id", fdc_id)
                .in_("nutrient_id", nutrient_ids)
                .execute()
            )
        except Exception:
            return out
        for row in (r.data or []):
            nid = row.get("nutrient_id")
            amount = _float_or_none(row.get("amount"))
            if nid == NUTRIENT_ID_ENERGY_KCAL:
                out["calories"] = amount
            elif nid == NUTRIENT_ID_PROTEIN:
                out["protein_g"] = amount
            elif nid == NUTRIENT_ID_CARB:
                out["carbs_g"] = amount
            elif nid == NUTRIENT_ID_FAT:
                out["fat_g"] = amount
        return out

    def get_serving_info(self, fdc_id: int) -> Dict[str, Any]:
        """
        Get serving_weight_grams and optional display text.
        Prefer usda_branded_food (serving_size, household_serving_fulltext); else usda_food_portion (gram_weight).
        """
        result = {"serving_weight_grams": None, "basis": "100g", "portion_description": None}

        # 1) Try branded_food
        try:
            r = (
                self.client.table("usda_branded_food")
                .select("serving_size, serving_size_unit, household_serving_fulltext, short_description")
                .eq("fdc_id", fdc_id)
                .limit(1)
                .execute()
            )
            if r.data and len(r.data) > 0:
                row = r.data[0]
                unit = (str(row.get("serving_size_unit") or "")).lower()
                size = _float_or_none(row.get("serving_size"))
                if size is not None:
                    if unit in ("g", "gram", "grams"):
                        result["serving_weight_grams"] = size
                    elif unit in ("ml", "milliliter", "milliliters"):
                        # Approximate 1 ml water = 1 g; use as-is for consistency
                        result["serving_weight_grams"] = size
                    else:
                        result["serving_weight_grams"] = size  # store anyway; display can show unit
                    result["basis"] = "serving"
                result["portion_description"] = (
                    row.get("household_serving_fulltext") or row.get("short_description")
                )
                return result
        except Exception:
            pass

        # 2) Fall back to food_portion (first by seq_num)
        try:
            r = (
                self.client.table("usda_food_portion")
                .select("gram_weight, portion_description, modifier, measure_unit_id")
                .eq("fdc_id", fdc_id)
                .order("seq_num")
                .limit(1)
                .execute()
            )
            if r.data and len(r.data) > 0:
                row = r.data[0]
                gw = _float_or_none(row.get("gram_weight"))
                if gw is not None:
                    result["serving_weight_grams"] = gw
                    result["basis"] = "serving"
                desc = row.get("portion_description") or row.get("modifier")
                if desc:
                    result["portion_description"] = desc
                return result
        except Exception:
            pass

        return result
