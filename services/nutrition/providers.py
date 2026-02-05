"""
External nutrition data providers.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Protocol, Tuple

import requests

from .types import NutritionResult

try:
    from supabase import Client as SupabaseClient
except ImportError:
    SupabaseClient = None  # type: ignore[misc, assignment]


class NutritionProvider(Protocol):
    source: str

    def lookup(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        ...


def _first_number(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


class USDASupabaseProvider:
    """
    USDA nutrition from Supabase (usda_food, usda_food_nutrient, usda_nutrient,
    plus food_portion, measure_unit, food_category, branded_food for accuracy).
    """

    source = "usda_db"

    def __init__(self, supabase: SupabaseClient):
        if SupabaseClient is None:
            raise ImportError("supabase package required for USDASupabaseProvider")
        from data.usda_repository import USDARepository
        self.repo = USDARepository(supabase)

    def lookup(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        q = (query or "").strip()
        if not q:
            return None
        foods = self.repo.search_food(q, limit=5)
        if not foods:
            return None
        best = foods[0]
        fdc_id = best.get("fdc_id")
        if fdc_id is None:
            return None
        try:
            fdc_id = int(fdc_id)
        except (TypeError, ValueError):
            return None
        macros = self.repo.get_macros(fdc_id)
        if (
            macros.get("calories") is None
            and macros.get("protein_g") is None
            and macros.get("carbs_g") is None
            and macros.get("fat_g") is None
        ):
            return None
        serving = self.repo.get_serving_info(fdc_id)
        resolved_name = best.get("description") or serving.get("portion_description")
        raw: Dict[str, Any] = {
            "fdc_id": fdc_id,
            "data_type": best.get("data_type"),
            "food_category_id": best.get("food_category_id"),
        }
        return NutritionResult(
            calories=macros.get("calories"),
            protein_g=macros.get("protein_g"),
            carbs_g=macros.get("carbs_g"),
            fat_g=macros.get("fat_g"),
            source=self.source,
            confidence=0.7,
            basis=serving.get("basis") or "serving",
            serving_weight_grams=serving.get("serving_weight_grams"),
            resolved_name=resolved_name,
            raw=raw,
        )


class USDAFoodDataCentralProvider:
    """
    USDA FoodData Central search provider.
    Uses the FDC API to return macro nutrients for generic/branded foods.
    """

    source = "usda_fdc"

    def __init__(self, api_key: str, timeout_s: float = 8.0):
        self.api_key = (api_key or "").strip()
        self.timeout_s = timeout_s

    def lookup(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        if not self.api_key:
            return None
        q = (query or "").strip()
        if not q:
            return None

        # FDC search endpoint
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {"api_key": self.api_key}
        payload = {
            "query": q,
            "pageSize": 5,
        }
        try:
            resp = requests.post(url, params=params, json=payload, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        foods = data.get("foods") or []
        if not foods:
            return None

        best = foods[0]
        nutrients = best.get("foodNutrients") or []

        # Map nutrient names to our macros
        def pick(names: List[str]) -> Optional[float]:
            for n in nutrients:
                nm = str(n.get("nutrientName") or "").lower()
                if any(t.lower() in nm for t in names):
                    return _first_number(n.get("value"))
            return None

        calories = pick(["energy"])  # usually kcal
        protein = pick(["protein"])
        carbs = pick(["carbohydrate"])
        fat = pick(["total lipid", "fat"])

        # Serving basis if available; else treat as per serving-like record.
        serving_weight_grams = _first_number(best.get("servingSize"))
        serving_unit = str(best.get("servingSizeUnit") or "").lower()
        basis = "serving"
        if serving_weight_grams is None and serving_unit:
            # Some entries are per 100g-ish; keep as serving but without grams.
            serving_weight_grams = None

        resolved_name = best.get("description") or best.get("lowercaseDescription")

        if calories is None and protein is None and carbs is None and fat is None:
            return None

        return NutritionResult(
            calories=calories,
            protein_g=protein,
            carbs_g=carbs,
            fat_g=fat,
            source=self.source,
            confidence=0.6,
            basis=basis,
            serving_weight_grams=serving_weight_grams,
            resolved_name=resolved_name,
            raw={"fdcId": best.get("fdcId"), "dataType": best.get("dataType"), "servingSizeUnit": serving_unit},
        )


class OpenFoodFactsProvider:
    """Open Food Facts name search provider (best for packaged foods)."""

    source = "open_food_facts"

    def __init__(self, base_url: str = "https://world.openfoodfacts.org", timeout_s: float = 8.0):
        self.base_url = (base_url or "https://world.openfoodfacts.org").rstrip("/")
        self.timeout_s = timeout_s

    def lookup(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        q = (query or "").strip()
        if not q:
            return None

        url = f"{self.base_url}/cgi/search.pl"
        params = {
            "search_terms": q,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
        }
        try:
            resp = requests.get(url, params=params, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        products = data.get("products") or []
        if not products:
            return None

        # Pick first product with energy-kcal_100g
        picked: Optional[Dict[str, Any]] = None
        for p in products:
            nutr = p.get("nutriments") or {}
            if nutr.get("energy-kcal_100g") is not None or nutr.get("energy-kcal") is not None:
                picked = p
                break
        if not picked:
            picked = products[0]

        nutr = picked.get("nutriments") or {}
        calories_100g = _first_number(nutr.get("energy-kcal_100g") or nutr.get("energy-kcal"))
        protein_100g = _first_number(nutr.get("proteins_100g") or nutr.get("proteins"))
        carbs_100g = _first_number(nutr.get("carbohydrates_100g") or nutr.get("carbohydrates"))
        fat_100g = _first_number(nutr.get("fat_100g") or nutr.get("fat"))

        if calories_100g is None and protein_100g is None and carbs_100g is None and fat_100g is None:
            return None

        # OFF is usually per 100g
        resolved_name = picked.get("product_name") or picked.get("generic_name") or picked.get("brands")
        return NutritionResult(
            calories=calories_100g,
            protein_g=protein_100g,
            carbs_g=carbs_100g,
            fat_g=fat_100g,
            source=self.source,
            confidence=0.45,
            basis="100g",
            serving_weight_grams=100.0,
            resolved_name=resolved_name,
            raw={"code": picked.get("code"), "brands": picked.get("brands")},
        )


class NutritionixProvider:
    """Nutritionix natural language nutrients provider (paid/free-tier depending on account)."""

    source = "nutritionix"

    def __init__(self, app_id: str, api_key: str, timeout_s: float = 10.0):
        self.app_id = (app_id or "").strip()
        self.api_key = (api_key or "").strip()
        self.timeout_s = timeout_s

    def lookup(self, *, query: str, restaurant: Optional[str] = None) -> Optional[NutritionResult]:
        if not self.app_id or not self.api_key:
            return None
        q = (query or "").strip()
        if not q:
            return None

        url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
        headers = {"x-app-id": self.app_id, "x-app-key": self.api_key, "Content-Type": "application/json"}
        payload: Dict[str, Any] = {"query": q}
        if restaurant:
            # This doesn't guarantee restaurant specificity but helps contextually.
            payload["query"] = f"{q} from {restaurant}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        foods = data.get("foods") or []
        if not foods:
            return None

        f = foods[0]
        calories = _first_number(f.get("nf_calories"))
        protein = _first_number(f.get("nf_protein"))
        carbs = _first_number(f.get("nf_total_carbohydrate"))
        fat = _first_number(f.get("nf_total_fat"))
        grams = _first_number(f.get("serving_weight_grams"))
        resolved_name = f.get("food_name")

        if calories is None and protein is None and carbs is None and fat is None:
            return None

        return NutritionResult(
            calories=calories,
            protein_g=protein,
            carbs_g=carbs,
            fat_g=fat,
            source=self.source,
            confidence=0.7,
            basis="serving",
            serving_weight_grams=grams,
            resolved_name=resolved_name,
            raw={"brand_name": f.get("brand_name"), "serving_unit": f.get("serving_unit"), "serving_qty": f.get("serving_qty")},
        )


def build_default_providers(supabase: SupabaseClient) -> List[NutritionProvider]:
    providers: List[NutritionProvider] = []

    # USDA from Supabase (skip if tables were dropped; set USE_USDA_SUPABASE=false)
    use_usda_supabase = os.getenv("USE_USDA_SUPABASE", "true").strip().lower() != "false"
    if supabase is not None and use_usda_supabase:
        try:
            providers.append(USDASupabaseProvider(supabase))
        except Exception:
            pass

    # Open Food Facts is public
    providers.append(OpenFoodFactsProvider(base_url=os.getenv("OPENFOODFACTS_BASE_URL", "https://world.openfoodfacts.org")))

    nix_id = os.getenv("NUTRITIONIX_APP_ID", "").strip()
    nix_key = os.getenv("NUTRITIONIX_API_KEY", "").strip()
    if nix_id and nix_key:
        providers.append(NutritionixProvider(app_id=nix_id, api_key=nix_key))

    return providers

