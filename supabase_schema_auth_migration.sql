-- Migration: Add Supabase Auth Integration
-- This migration adds support for Supabase Auth while keeping the custom users table
-- Run this in Supabase SQL Editor after enabling phone authentication

-- Step 1: Add auth_user_id column to link to Supabase Auth users
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Step 2: Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON users(auth_user_id);

-- Step 3: Make auth_user_id unique (one-to-one relationship)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_auth_user_id_unique ON users(auth_user_id) 
WHERE auth_user_id IS NOT NULL;

-- Step 4: Create function to automatically create user record when Supabase Auth user is created
-- This will be called via database trigger or manually during registration
CREATE OR REPLACE FUNCTION sync_auth_user_to_custom_users()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create if it doesn't exist (prevent duplicates)
    INSERT INTO users (auth_user_id, phone_number, email, name, timezone, is_active)
    VALUES (
        NEW.id,
        COALESCE(NEW.phone, ''),
        COALESCE(NEW.email, ''),
        COALESCE(NEW.raw_user_meta_data->>'name', ''),
        COALESCE(NEW.raw_user_meta_data->>'timezone', 'UTC'),
        TRUE
    )
    ON CONFLICT (auth_user_id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 5: Create trigger to sync auth.users to custom users table
-- Note: This is optional - we can also do it manually in code for more control
-- DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
-- CREATE TRIGGER on_auth_user_created
--     AFTER INSERT ON auth.users
--     FOR EACH ROW
--     EXECUTE FUNCTION sync_auth_user_to_custom_users();

-- Step 6: Create function to get user_id from auth_user_id (helper function)
CREATE OR REPLACE FUNCTION get_user_id_from_auth(auth_uuid UUID)
RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    SELECT id INTO user_id FROM users WHERE auth_user_id = auth_uuid LIMIT 1;
    RETURN user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 7: Update RLS policies to work with auth_user_id
-- Note: Existing RLS policies should still work, but we can add auth-based ones if needed

-- Migration complete!
-- After running this:
-- 1. Existing users will have NULL auth_user_id (they'll need to migrate)
-- 2. New users will be created via Supabase Auth and linked via auth_user_id
-- 3. You can gradually migrate existing users by creating auth accounts for them
