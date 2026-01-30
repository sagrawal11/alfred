-- ============================================================================
-- Nutrition Pipeline Additions (Milestone A/C)
-- Adds: nutrition_cache, food_log_metadata, food_image_uploads (optional later)
-- ============================================================================

-- Cache resolved nutrition results to avoid repeated external API calls
CREATE TABLE IF NOT EXISTS nutrition_cache (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    restaurant TEXT,
    source TEXT NOT NULL, -- 'usda_fdc' | 'open_food_facts' | 'nutritionix' | others
    resolved_name TEXT,
    basis TEXT NOT NULL DEFAULT 'serving', -- 'serving' | '100g'
    serving_weight_grams NUMERIC CHECK (serving_weight_grams IS NULL OR serving_weight_grams >= 0),
    calories NUMERIC CHECK (calories IS NULL OR calories >= 0),
    protein NUMERIC CHECK (protein IS NULL OR protein >= 0),
    carbs NUMERIC CHECK (carbs IS NULL OR carbs >= 0),
    fat NUMERIC CHECK (fat IS NULL OR fat >= 0),
    confidence NUMERIC DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    raw JSONB,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(query, restaurant, source)
);

CREATE INDEX IF NOT EXISTS idx_nutrition_cache_query ON nutrition_cache(query);
CREATE INDEX IF NOT EXISTS idx_nutrition_cache_query_restaurant ON nutrition_cache(query, restaurant);
CREATE INDEX IF NOT EXISTS idx_nutrition_cache_expires_at ON nutrition_cache(expires_at);

-- Store metadata about each food_log (where numbers came from, confidence, etc.)
CREATE TABLE IF NOT EXISTS food_log_metadata (
    id BIGSERIAL PRIMARY KEY,
    food_log_id INTEGER REFERENCES food_logs(id) ON DELETE CASCADE NOT NULL,
    source TEXT NOT NULL,
    confidence NUMERIC DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    basis TEXT,
    serving_weight_grams NUMERIC CHECK (serving_weight_grams IS NULL OR serving_weight_grams >= 0),
    resolved_name TEXT,
    raw_query TEXT,
    raw JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_food_log_metadata_food_log_id ON food_log_metadata(food_log_id);

-- Track uploaded food images (Milestone B/C)
CREATE TABLE IF NOT EXISTS food_image_uploads (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    bucket TEXT NOT NULL,
    path TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT DEFAULT 0 CHECK (size_bytes >= 0),
    kind TEXT, -- 'label'|'receipt'|'plated'|'unknown'
    status TEXT NOT NULL DEFAULT 'uploaded', -- 'uploaded'|'processed'|'failed'
    original_filename TEXT,
    extracted JSONB, -- populated in Milestone C
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_food_image_uploads_user_id ON food_image_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_food_image_uploads_created_at ON food_image_uploads(created_at);

