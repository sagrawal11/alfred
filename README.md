# Alfred (SMS Assistant)

Alfred is a personalized SMS-first assistant that feels like a real person, but is grounded in your data. You text naturally; Alfred logs, remembers, and retrieves your history from Supabase, and helps you stay on top of your life without making you manage a system.

This repo contains:
- A **Flask** app that powers Twilio SMS webhooks + a web dashboard
- A **Supabase** backend (Postgres + Storage)
- A black/white **dashboard UI** (Trends, Preferences, Settings, Integrations (Coming Soon), Pricing)
- A generalized nutrition pipeline + dashboard image-based food logging
- **Stripe** subscriptions (Free/Core/Pro) with billing state stored on `public.users`
- An **agent mode** (tool-calling + durable memory) powered by OpenAI (`gpt-4o` voice, `gpt-4o-mini` internal steps)

---

## Product philosophy

Most tools are trackers. Alfred is a companion that reduces mental load:
- remembers what matters
- nudges gently
- closes open loops
- gives you the “what now?” answer without dashboards

---

## High-level architecture

```text
Twilio SMS  ->  Flask (/webhook/twilio)  ->  Alfred brain  ->  TwiML response
                                   |
                                   +-> Supabase (users + logs + memory + billing)
                                   +-> Background jobs (nudges/digests/sync)

Web dashboard -> Flask (/dashboard/...) -> Supabase
```

There are currently two “brains”:

- **Classic pipeline** (always available): intent classification → entity extraction → handler routing
  - Implemented in `core/processor.py`
  - Used for onboarding, STOP/HELP/START behaviors, and as a fallback

- **Agent mode** (new, optional): tool-calling orchestration + durable memory
  - Implemented in `services/agent/orchestrator.py`
  - Uses:
    - `gpt-4o` for Alfred’s final user-facing voice
    - `gpt-4o-mini` for routing + summarization
    - `text-embedding-3-small` for memory embeddings

---

## Key user-facing features

### SMS + “Chat Test” simulator
- SMS webhook: `/webhook/twilio`
- Web chat simulator: `/dashboard/chat` → `/dashboard/api/chat`
- Both are wired to the same underlying processing path and support multi-message replies.

### Onboarding (account-first)
- Web users create an account first, then onboarding happens via SMS/chat when `users.onboarding_complete = false`.
- Onboarding flow lives in `core/onboarding.py`.

### Logging + queries
- Food, water, workouts, sleep, todos/reminders are stored in Supabase.
- Trends page shows a real chart + activity log from DB.

### Generalized nutrition
- Tiered resolver with caching:
  - **USDA database** (Supabase: `usda_food`, `usda_food_nutrient`, `usda_nutrient`, plus portion/category/branded tables) → Open Food Facts → Nutritionix API (optional)
- Run `supabase_schema_usda.sql` and import the 7 USDA CSVs into Supabase (one-time). Cache table: `nutrition_cache`

### Dashboard image-based food logging
- Upload a label/receipt/food photo in the dashboard
- Stored in Supabase Storage + metadata tables
- Processed with OpenAI vision to structured logs + metadata

### Stripe subscriptions + plan visibility
- Stripe Checkout for Core/Pro
- Webhook updates billing state on `public.users` (plan + interval + subscription IDs)
- Pricing page shows the user’s current plan badge

---

## Repository layout (important folders)

- `app.py`: Flask entrypoint + Twilio webhook routes + service initialization
- `web/`: dashboard routes, auth, trends APIs
- `templates/` + `static/`: dashboard UI (black/white + Butler font)
- `core/`: classic message processor, onboarding, session manager
- `services/agent/`: agent mode orchestrator + validated tool execution
- `data/`: Supabase repositories (all DB reads/writes)
- `services/nutrition/` + `services/vision/`: nutrition resolver + vision extraction pipeline

---

## Supabase schema / migrations (run in SQL editor)

Baseline + existing features:
- `supabase_schema_complete.sql` (full schema from scratch)
- `supabase_schema_onboarding_prefs.sql` (onboarding + preferences fields)
- `supabase_schema_phase6_additions.sql` (older auth fields; some may be unused now)
- `supabase_schema_nutrition_pipeline.sql` (nutrition cache + image uploads + log metadata)
- `supabase_schema_usda.sql` (USDA food/nutrient/portion/category/branded tables for nutrition resolution; then import all 7 CSVs via Dashboard)
- `supabase_schema_stripe_billing.sql` (Stripe billing columns on `public.users`)

Agent mode additions:
- `supabase_schema_agent_memory.sql` (memory tables + pgvector + RLS)
- `supabase_schema_agent_usage.sql` (monthly usage metering + RPC)

---

## Environment variables

Start from `config/env_template.txt` and copy into `.env` (format must be `KEY=value`).

### Required (basic)
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `FLASK_SECRET_KEY`
- `BASE_URL` (needed for Stripe and some redirects)

### OpenAI (agent + NLP)
- `OPENAI_API_KEY`

Agent mode configuration:
- `AGENT_MODE_ENABLED=true|false`
- `OPENAI_MODEL_VOICE=gpt-4o`
- `OPENAI_MODEL_ROUTER=gpt-4o-mini`
- `OPENAI_MODEL_SUMMARIZER=gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

### Twilio (SMS)
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

### Stripe
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_CORE_MONTHLY`
- `STRIPE_PRICE_CORE_ANNUAL`
- `STRIPE_PRICE_PRO_MONTHLY`
- `STRIPE_PRICE_PRO_ANNUAL`

### Nutrition
- Food macros are resolved from **USDA data in Supabase** (run `supabase_schema_usda.sql` and import the 7 CSVs: food, food_nutrient, nutrient, food_portion, measure_unit, food_category, branded_food), then Open Food Facts, then Nutritionix API if configured.
- `OPENFOODFACTS_BASE_URL` (default `https://world.openfoodfacts.org`)
- `NUTRITIONIX_APP_ID` / `NUTRITIONIX_API_KEY` (optional fallback)

### Dashboard uploads (optional but recommended if using image logging)
- `FOOD_IMAGE_BUCKET`
- `FOOD_IMAGE_MAX_BYTES`

---

## Local development

### 1) Create + activate venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run the app

```bash
python app.py
```

App:
- Home: `http://localhost:5001/`
- Dashboard login: `http://localhost:5001/dashboard/login`

### 3) Stripe webhook (local)

```bash
stripe listen --forward-to localhost:5001/stripe/webhook
```

---

## Agent mode behavior (important)

When `AGENT_MODE_ENABLED=true`:
- Web chat (`/dashboard/api/chat`) uses the agent **only if onboarding is complete**
- Twilio SMS (`/webhook/twilio`) uses the agent **only if onboarding is complete**
- STOP/HELP/START still use the classic behavior for safety/consistency

Durable memory:
- `user_memory_state` stores a short running summary used each turn
- `user_memory_items` stores specific facts/preferences/plans
- `user_memory_embeddings` stores embeddings for semantic recall (pgvector)

Metering:
- `user_usage_monthly` tracks “turns” per month
- Quota defaults (can be tuned):
  - Free: 50 turns/month
  - Core: 1000 turns/month
  - Pro: unlimited (fair use)

---

## Testing

```bash
pytest -q
```

---

## Troubleshooting

### “No such price: prod_…”
Your `.env` has a Product ID instead of a Price ID. Stripe env vars must be `price_...`.

### Gemini import errors on older Python
Gemini is optional. The project runs OpenAI-first; Gemini imports are guarded so OpenAI-only deployments still run.

### Trends chart shows zeros but activity log works
Usually means logs exist but numeric macro fields are null/empty; the trend series sums numeric columns.

---

## License

See `LICENSE`.