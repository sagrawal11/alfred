-- ============================================================================
-- Alfred Onboarding + Preferences Migration
-- Adds onboarding fields to users and preference fields to user_preferences
-- Safe to run multiple times (IF NOT EXISTS)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Users: onboarding fields (account-first SMS onboarding)
-- ---------------------------------------------------------------------------
ALTER TABLE users
ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS reminder_style_raw TEXT,
ADD COLUMN IF NOT EXISTS reminder_style_bucket TEXT,
ADD COLUMN IF NOT EXISTS voice_style_raw TEXT,
ADD COLUMN IF NOT EXISTS voice_style_bucket TEXT,
ADD COLUMN IF NOT EXISTS water_bottle_ml INTEGER,
ADD COLUMN IF NOT EXISTS morning_checkin_hour INTEGER,
ADD COLUMN IF NOT EXISTS location_name TEXT,
ADD COLUMN IF NOT EXISTS location_lat DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS location_lon DOUBLE PRECISION;

-- ---------------------------------------------------------------------------
-- User preferences: additional per-user settings
-- ---------------------------------------------------------------------------
ALTER TABLE user_preferences
ADD COLUMN IF NOT EXISTS default_water_goal_ml INTEGER,
ADD COLUMN IF NOT EXISTS default_calories_goal INTEGER,
ADD COLUMN IF NOT EXISTS default_protein_goal INTEGER,
ADD COLUMN IF NOT EXISTS default_carbs_goal INTEGER,
ADD COLUMN IF NOT EXISTS default_fat_goal INTEGER,
ADD COLUMN IF NOT EXISTS weekly_digest_day INTEGER,
ADD COLUMN IF NOT EXISTS weekly_digest_hour INTEGER,
ADD COLUMN IF NOT EXISTS morning_include_reminders BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS morning_include_weather BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS morning_include_quote BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS last_morning_checkin_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_weekly_digest_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS freeform_goal TEXT;

