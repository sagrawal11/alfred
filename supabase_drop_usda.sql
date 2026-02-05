-- ============================================================================
-- Drop all USDA FoodData Central tables from Supabase
-- Run this in Supabase SQL Editor when you want to remove USDA data (e.g. to
-- save storage; re-add later with supabase_schema_usda.sql + CSV import).
-- Then set USE_USDA_SUPABASE=false in .env so the app skips the USDA provider.
-- ============================================================================

DROP TABLE IF EXISTS usda_branded_food;
DROP TABLE IF EXISTS usda_food_portion;
DROP TABLE IF EXISTS usda_food_nutrient;
DROP TABLE IF EXISTS usda_food_category;
DROP TABLE IF EXISTS usda_measure_unit;
DROP TABLE IF EXISTS usda_nutrient;
DROP TABLE IF EXISTS usda_food;
