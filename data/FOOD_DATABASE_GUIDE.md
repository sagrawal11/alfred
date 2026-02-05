# Food and nutrition in Alfred

Food logging gets **macros** (calories, protein, carbs, fat) from a tiered nutrition resolver:

1. **USDA database (Supabase)** – Optional primary source. Run `supabase_schema_usda.sql` in the Supabase SQL editor to create the tables, then import all 7 CSVs from `data/USDA/` via the Dashboard (Table Editor → Import CSV):
   - `food.csv` → `usda_food`
   - `food_nutrient.csv` → `usda_food_nutrient`
   - `nutrient.csv` → `usda_nutrient`
   - `food_portion.csv` → `usda_food_portion`
   - `measure_unit.csv` → `usda_measure_unit`
   - `food_category.csv` → `usda_food_category`
   - `branded_food.csv` → `usda_branded_food`

2. **Open Food Facts** – Public API (packaged foods).

3. **Nutritionix API** – Optional (set `NUTRITIONIX_APP_ID` and `NUTRITIONIX_API_KEY` in `.env`).

**Running without USDA tables:** If you dropped the USDA tables (e.g. to save storage), set `USE_USDA_SUPABASE=false` in `.env`. Nutrition will use Open Food Facts and Nutritionix only. To remove the tables, run `supabase_drop_usda.sql` in the Supabase SQL editor.

Resolved results are cached in the `nutrition_cache` table. See the main [README](../README.md) for environment variables and schema overview.
