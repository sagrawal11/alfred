-- ============================================================================
-- USDA FoodData Central tables for nutrition resolution
-- Create these tables, then import the 7 CSVs via Supabase Dashboard (Table Editor → Import CSV).
-- No foreign keys are enforced so you can import in any order and use a trimmed food.csv
-- (e.g. only "necessary" foods) while still importing full food_portion/branded_food CSVs.
-- ============================================================================

-- Core: food list (search by description)
CREATE TABLE IF NOT EXISTS usda_food (
    fdc_id BIGINT PRIMARY KEY,
    data_type TEXT,
    description TEXT,
    food_category_id TEXT,
    publication_date DATE
);
CREATE INDEX IF NOT EXISTS idx_usda_food_description_lower ON usda_food(LOWER(description));
CREATE INDEX IF NOT EXISTS idx_usda_food_data_type ON usda_food(data_type);

-- Nutrient definitions (id -> name, unit)
CREATE TABLE IF NOT EXISTS usda_nutrient (
    id INTEGER PRIMARY KEY,
    name TEXT,
    unit_name TEXT,
    nutrient_nbr TEXT,
    rank NUMERIC
);

-- Food -> nutrient amounts (macros)
CREATE TABLE IF NOT EXISTS usda_food_nutrient (
    id BIGINT PRIMARY KEY,
    fdc_id BIGINT NOT NULL,
    nutrient_id INTEGER NOT NULL,
    amount NUMERIC,
    data_points TEXT,
    derivation_id TEXT,
    min NUMERIC,
    max NUMERIC,
    median NUMERIC,
    loq NUMERIC,
    footnote TEXT,
    min_year_acquired TEXT,
    percent_daily_value NUMERIC
);
CREATE INDEX IF NOT EXISTS idx_usda_food_nutrient_fdc_nutrient ON usda_food_nutrient(fdc_id, nutrient_id);
CREATE INDEX IF NOT EXISTS idx_usda_food_nutrient_fdc_id ON usda_food_nutrient(fdc_id);

-- Measure units (cup, tablespoon, etc.)
CREATE TABLE IF NOT EXISTS usda_measure_unit (
    id TEXT PRIMARY KEY,
    name TEXT
);

-- Food categories (for display/ranking)
CREATE TABLE IF NOT EXISTS usda_food_category (
    id INTEGER PRIMARY KEY,
    code TEXT,
    description TEXT
);

-- Portion sizes per food (gram_weight = serving_weight_grams)
CREATE TABLE IF NOT EXISTS usda_food_portion (
    id BIGINT PRIMARY KEY,
    fdc_id BIGINT NOT NULL,
    seq_num INTEGER,
    amount NUMERIC,
    measure_unit_id TEXT,
    portion_description TEXT,
    modifier TEXT,
    gram_weight NUMERIC,
    data_points TEXT,
    footnote TEXT,
    min_year_acquired TEXT
);
CREATE INDEX IF NOT EXISTS idx_usda_food_portion_fdc_id ON usda_food_portion(fdc_id);

-- Branded food extra fields (serving_size, household_serving_fulltext)
CREATE TABLE IF NOT EXISTS usda_branded_food (
    fdc_id BIGINT PRIMARY KEY,
    brand_owner TEXT,
    brand_name TEXT,
    subbrand_name TEXT,
    gtin_upc TEXT,
    ingredients TEXT,
    not_a_significant_source_of TEXT,
    serving_size NUMERIC,
    serving_size_unit TEXT,
    household_serving_fulltext TEXT,
    branded_food_category TEXT,
    data_source TEXT,
    package_weight TEXT,
    modified_date TEXT,
    available_date TEXT,
    market_country TEXT,
    discontinued_date TEXT,
    preparation_state_code TEXT,
    trade_channel TEXT,
    short_description TEXT,
    material_code TEXT
);
