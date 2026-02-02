-- ============================================================================
-- Alfred Agent Memory Schema (Durable Memory + Embeddings)
-- ============================================================================
-- Purpose:
-- - Store a per-user running summary (cheap context every turn)
-- - Store append-only memory items (facts/preferences/plans)
-- - Store embeddings for semantic recall (pgvector)
--
-- Safe to run multiple times where possible.
-- Run in Supabase SQL editor.
-- ============================================================================

-- Enable pgvector if available (Supabase supports this).
DO $$
BEGIN
  BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
  EXCEPTION WHEN insufficient_privilege THEN
    -- If extension creation is not permitted in this environment, embeddings table
    -- will still be created, but the vector column/index may need adjustment.
    RAISE NOTICE 'Could not create extension vector (insufficient privileges).';
  END;
END $$;

-- ============================================================================
-- user_memory_state: 1 row per user (running summary + optional style profile)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_memory_state (
  user_id INTEGER PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  summary TEXT NOT NULL DEFAULT '',
  style_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_state_user_id ON public.user_memory_state(user_id);

-- ============================================================================
-- user_memory_items: append-only memory entries (facts/preferences/plans/etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_memory_items (
  id BIGSERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  kind TEXT NOT NULL, -- e.g. 'fact'|'preference'|'plan'|'relationship'|'note'
  content TEXT NOT NULL,
  source TEXT, -- e.g. 'sms'|'web'
  importance NUMERIC DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_items_user_id_created_at ON public.user_memory_items(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_memory_items_user_id_kind ON public.user_memory_items(user_id, kind);

-- ============================================================================
-- user_memory_embeddings: 1 embedding per memory item (semantic search)
-- ============================================================================
-- Note: text-embedding-3-small is typically 1536 dims. Keep consistent in code.
CREATE TABLE IF NOT EXISTS public.user_memory_embeddings (
  memory_item_id BIGINT PRIMARY KEY REFERENCES public.user_memory_items(id) ON DELETE CASCADE,
  model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create a vector index only if pgvector is installed.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    -- ivfflat requires ANALYZE and works best with enough rows; fine to create now.
    BEGIN
      EXECUTE 'CREATE INDEX IF NOT EXISTS idx_user_memory_embeddings_ivfflat ON public.user_memory_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)';
    EXCEPTION WHEN undefined_column OR undefined_object THEN
      -- If vector type isn't available for some reason, skip.
      RAISE NOTICE 'Skipping vector index creation (vector type not available).';
    END;
  ELSE
    RAISE NOTICE 'pgvector extension not present; embeddings will not be index-accelerated.';
  END IF;
END $$;

-- ============================================================================
-- RLS
-- ============================================================================
ALTER TABLE public.user_memory_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_memory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_memory_embeddings ENABLE ROW LEVEL SECURITY;

-- Service role full access
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'user_memory_state' AND policyname = 'Service role full access memory state'
  ) THEN
    EXECUTE 'CREATE POLICY "Service role full access memory state" ON public.user_memory_state FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'user_memory_items' AND policyname = 'Service role full access memory items'
  ) THEN
    EXECUTE 'CREATE POLICY "Service role full access memory items" ON public.user_memory_items FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'user_memory_embeddings' AND policyname = 'Service role full access memory embeddings'
  ) THEN
    EXECUTE 'CREATE POLICY "Service role full access memory embeddings" ON public.user_memory_embeddings FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- Authenticated users: allow access to rows that belong to their linked custom user id.
-- This assumes `public.users.auth_user_id` is present (see `supabase_schema_auth_migration.sql`).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'auth_user_id'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'user_memory_state' AND policyname = 'Users can manage own memory state'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "Users can manage own memory state"
        ON public.user_memory_state FOR ALL TO authenticated
        USING (
          EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = user_memory_state.user_id AND u.auth_user_id = auth.uid()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = user_memory_state.user_id AND u.auth_user_id = auth.uid()
          )
        )
      $pol$;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'user_memory_items' AND policyname = 'Users can manage own memory items'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "Users can manage own memory items"
        ON public.user_memory_items FOR ALL TO authenticated
        USING (
          EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = user_memory_items.user_id AND u.auth_user_id = auth.uid()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = user_memory_items.user_id AND u.auth_user_id = auth.uid()
          )
        )
      $pol$;
    END IF;

    -- Embeddings table is linked through memory_item_id → user_memory_items.user_id
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'user_memory_embeddings' AND policyname = 'Users can manage own memory embeddings'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "Users can manage own memory embeddings"
        ON public.user_memory_embeddings FOR ALL TO authenticated
        USING (
          EXISTS (
            SELECT 1
            FROM public.user_memory_items mi
            JOIN public.users u ON u.id = mi.user_id
            WHERE mi.id = user_memory_embeddings.memory_item_id AND u.auth_user_id = auth.uid()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1
            FROM public.user_memory_items mi
            JOIN public.users u ON u.id = mi.user_id
            WHERE mi.id = user_memory_embeddings.memory_item_id AND u.auth_user_id = auth.uid()
          )
        )
      $pol$;
    END IF;
  ELSE
    RAISE NOTICE 'Column public.users.auth_user_id not found; skipping authenticated-user RLS policies for memory tables.';
  END IF;
END $$;

