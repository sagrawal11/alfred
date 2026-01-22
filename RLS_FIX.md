# Fixing Row Level Security (RLS) Issues

## Problem
You're getting RLS errors: `new row violates row-level security policy for table "food_logs"`

## Solution Options

### Option 1: Use Service Role Key (Recommended for Single-User System)

The service role key bypasses RLS policies. Make sure your `SUPABASE_KEY` environment variable is set to the **service role key**, not the anon key.

1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy the **service_role** key (NOT the anon key)
4. Update your `.env` file or Koyeb environment variables:
   ```
   SUPABASE_KEY=your_service_role_key_here
   ```

The service role key typically starts with `eyJ...` and is much longer than the anon key.

### Option 2: Disable RLS on Tables

If you prefer to keep using the anon key, you can disable RLS on your tables. Run this SQL in your Supabase SQL Editor:

```sql
-- Disable RLS on all tables
ALTER TABLE food_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE water_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE gym_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE reminders_todos DISABLE ROW LEVEL SECURITY;
ALTER TABLE sleep_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE facts DISABLE ROW LEVEL SECURITY;
ALTER TABLE assignments DISABLE ROW LEVEL SECURITY;
```

### Option 3: Create Permissive RLS Policies

If you want to keep RLS enabled, create policies that allow all operations:

```sql
-- Allow all operations on food_logs
CREATE POLICY "Allow all operations on food_logs" ON food_logs
FOR ALL USING (true) WITH CHECK (true);

-- Repeat for other tables...
```

## Recommendation

For a single-user system, **Option 1 (Service Role Key)** is the simplest and most secure approach. The service role key is meant for server-side operations and bypasses RLS, which is exactly what you need for your backend application.
