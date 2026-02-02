-- ============================================================================
-- Alfred Agent Usage Metering (Monthly turns)
-- ============================================================================
-- Purpose:
-- - Track monthly \"turns\" per user for quota enforcement (e.g. Core = 1000).
-- - Provide an atomic increment RPC for server-side usage accounting.
--
-- Run in Supabase SQL editor. Safe to run multiple times where possible.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_usage_monthly (
  user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  month_key TEXT NOT NULL, -- YYYY-MM (e.g., 2026-02)
  turns_used INTEGER NOT NULL DEFAULT 0 CHECK (turns_used >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, month_key)
);

CREATE INDEX IF NOT EXISTS idx_user_usage_monthly_user_month ON public.user_usage_monthly(user_id, month_key);

ALTER TABLE public.user_usage_monthly ENABLE ROW LEVEL SECURITY;

-- Service role full access
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'user_usage_monthly' AND policyname = 'Service role full access usage monthly'
  ) THEN
    EXECUTE 'CREATE POLICY "Service role full access usage monthly" ON public.user_usage_monthly FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- Authenticated users: allow access when linked via users.auth_user_id (if present).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'auth_user_id'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'user_usage_monthly' AND policyname = 'Users can read own usage monthly'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "Users can read own usage monthly"
        ON public.user_usage_monthly FOR SELECT TO authenticated
        USING (
          EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = user_usage_monthly.user_id AND u.auth_user_id = auth.uid()
          )
        )
      $pol$;
    END IF;
  END IF;
END $$;

-- Atomic increment RPC (server-side): increments turns_used and returns new value
CREATE OR REPLACE FUNCTION public.increment_user_usage_monthly(p_user_id integer, p_month_key text, p_delta integer)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  new_value integer;
BEGIN
  INSERT INTO public.user_usage_monthly (user_id, month_key, turns_used)
  VALUES (p_user_id, p_month_key, GREATEST(p_delta, 0))
  ON CONFLICT (user_id, month_key)
  DO UPDATE SET
    turns_used = public.user_usage_monthly.turns_used + GREATEST(p_delta, 0),
    updated_at = NOW()
  RETURNING turns_used INTO new_value;

  RETURN new_value;
END;
$$;

