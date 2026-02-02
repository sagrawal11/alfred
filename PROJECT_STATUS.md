## Alfred (SMS Assistant) — Project Status (Current)

**Last updated:** 2026-02-02  
**Overall status:** The product is functional end-to-end for core logging + dashboard + trends + billing (Stripe test mode verified). Some areas are intentionally placeholder (Integrations “Coming Soon” UI, password reset UI-only, feature gating by plan not yet enforced).

---

## Executive summary (what you can do right now)

Alfred currently supports:
- **Web auth + dashboard**: register/login, sidebar navigation, consistent black/white theme and Butler font.
- **Logging + stats**: food, water, workouts, sleep, todos/reminders (via SMS/chat test + DB persistence).
- **Generalized nutrition resolution**: local DB first, then external sources (USDA/Open Food Facts; Nutritionix optional) with caching.
- **Dashboard image uploads**: upload image → Supabase Storage → OpenAI vision extraction → create food logs + metadata.
- **Trends**: time-series chart + metric controls + real activity log from DB.
- **Pricing + Stripe Checkout**: Core/Pro subscriptions (test mode confirmed), webhook updates `public.users` plan fields.

You should think of Alfred today as:
- A working product with real data persistence and a polished dashboard UI
- With a few “productization” items still pending (feature gating, integrations UI enablement, some deeper analytics)

### Most important product decisions currently reflected in code
- **Phone verification removed**: registration does not require Twilio verification right now.
- **Registration UX**: no “registration successful” alert; users are taken straight to the dashboard on success.
- **Phone formatting**: US phone inputs are formatted live as `+1 (123) 456-7890` and normalized to E.164 on submit.
- **No “logged out successfully” banner**: logout returns you to landing/login without a flash banner.
- **Dashboard UX**: left sidebar navigation (no emojis), logo + “Alfred” at top, profile dropdown at bottom.
- **Settings vs Preferences split**: settings is account/profile/security UI; preferences is habit/behavior configuration UI.
- **Pricing copy**: Alfred is positioned as a daily life companion (mental load reducer), not a tracker/utility.

---

## Current product surfaces (user-facing)

### Landing page
- **Path**: `/`
- **File**: `templates/index.html`
- **Purpose**: marketing + signup/login modal.

### Dashboard: Activity (Calendar)
- **Path**: `/dashboard`
- **File**: `templates/dashboard/index.html`
- **Behavior**:
  - Calendar grid
  - Click a date → fetches `/dashboard/api/date/<date>` → shows daily breakdown (food, water, gym, todos/reminders, etc.)
- **Theme**: black/white, thick black borders, Butler font.

### Dashboard: Trends
- **Path**: `/dashboard/trends`
- **File**: `templates/dashboard/trends.html`
- **Server endpoints used**:
  - Chart series: `GET /dashboard/api/trends/series?timeframe=...&metric=...`
  - Activity log: `GET /dashboard/api/trends/activity?timeframe=...&metric=...`
- **UI**:
  - Top chart (Chart.js)
  - Timeframe dropdown (7d/14d/1m/1y)
  - Metric buttons (sleep/water/calories/protein/carbs/fat/todos/workouts/messages)
  - Activity log cards filtered to the selected metric
- **Notes**:
  - 1y view returns 12 monthly points (server aggregates daily stats into months).

### Dashboard: Integrations
- **Path**: `/dashboard/integrations`
- **File**: `templates/dashboard/integrations.html`
- **Current state**:
  - UI is deliberately organized into “Available Integrations” (empty) and “Coming Soon” (Fitbit/Google Calendar/Google Fit).
  - OAuth + sync code exists in `web/integrations.py`, but the current UI does not expose connect buttons.
  - When connect is re-enabled, the intended UX is: **OAuth opens in a right-side popup**, then the popup loads `templates/dashboard/oauth_done.html` to refresh the opener and auto-close.

### Dashboard: Preferences
- **Path**: `/dashboard/preferences`
- **File**: `templates/dashboard/preferences.html`
- **Backend endpoints used**:
  - `POST /dashboard/api/settings/preferences`
  - `POST /dashboard/api/settings/profile` (for morning check-in hour)
- **UI**:
  - Card-based layout (General / Quiet hours / Weekly digest / Goals / Morning text)
  - Inputs styled with thick black rounded borders (matches site)

### Dashboard: Settings
- **Path**: `/dashboard/settings`
- **File**: `templates/dashboard/settings.html`
- **Backend endpoint used**:
  - `POST /dashboard/api/settings/profile` (editable fields)
- **What’s editable**:
  - Name, Timezone, Location (including “use device location” lat/lon)
- **Password reset**:
  - **UI modal only** (collects email + shows “sent” message).
  - Actual Supabase password reset flow integration is intentionally deferred.

### Dashboard: Pricing (Billing)
- **Path**: `/dashboard/pricing`
- **File**: `templates/dashboard/pricing.html`
- **Behavior**:
  - Billing interval toggle (annual default)
  - “Choose Core/Pro” calls server to create Stripe Checkout session
  - **Current plan badge** shows from `user.plan` / `user.plan_interval`
  - If user is Core/Pro, hides “Most popular!” on Core and uses gold “Current plan” badge
- **Stripe endpoints**:
  - `POST /dashboard/api/billing/checkout`
  - `POST /dashboard/api/billing/portal` (optional)
  - `POST /stripe/webhook`

### UI/UX conventions (current dashboard)
- **Navigation**: left sidebar (`app-shell`/`sidebar`/`main-area` layout classes) with page links; no emojis.
- **Branding**: logo + “Alfred” at the very top of the sidebar, clickable back to `/dashboard`.
- **Typography**: Butler font enforced across pages, including input placeholders.
- **Controls**: thick black borders + rounded corners on inputs/selects; consistent spacing and card styles.
- **Main style file**: `static/dashboard/style.css`

---

## Authentication + session behavior (current)

### Registration flow
- The landing page registration form formats phone number as you type (US-only assumption).
- Server normalizes submitted phone number to E.164 before writing to Supabase.
- On success, the app redirects directly to `/dashboard` (no JS alert).

### Login flow
- Login uses phone (E.164) + password (depending on your configured auth manager).
- Dashboard routes require an authenticated session; unauthenticated users are redirected to landing/login.

### Password reset status
- The **Settings page reset password is UI-only** right now.
- Backend-backed Supabase password reset can be implemented later; current UI is designed to be polished without wiring.

---

## Stripe billing status (implemented + verified)

### What is implemented
- Stripe Checkout subscription creation for Core/Pro
- Stripe webhook signature verification
- Webhook updates to `public.users` billing columns:
  - `stripe_customer_id`
  - `stripe_subscription_id`
  - `stripe_price_id`
  - `stripe_subscription_status`
  - `stripe_current_period_end`
  - `stripe_cancel_at_period_end`
  - `plan` (`free`/`core`/`pro`)
  - `plan_interval` (`monthly`/`annual`)

### What was verified in local testing
- Checkout succeeded in test mode
- Webhook events delivered with HTTP 200 to `/stripe/webhook`
- Supabase `public.users` row updated correctly

### Docs / migration
- **Doc**: `stripe.md` (short checklist)
- **Migration**: `supabase_schema_stripe_billing.sql`

### What’s still pending (billing-related)
- **Feature gating** by plan (Core/Pro entitlements) is not enforced yet across the product; plan is stored and visible, but not used to restrict features.
- Optional: expose Billing Portal link in UI (Settings or Pricing).

---

## Stripe: exact routes + payloads (for debugging)

### Create checkout session
- **Route**: `POST /dashboard/api/billing/checkout`
- **Body (JSON)**: `{ "plan": "core" | "pro", "interval": "monthly" | "annual" }`
- **Response (JSON)**: `{ "url": "https://checkout.stripe.com/..." }`
- **Common failure mode**: “No such price: `prod_...`” means you put a Product ID where a Price ID is required. Env vars must be `price_...`.

### Create billing portal session (optional)
- **Route**: `POST /dashboard/api/billing/portal`
- **Response (JSON)**: `{ "url": "https://billing.stripe.com/..." }`

### Webhook
- **Route**: `POST /stripe/webhook`
- **Verification**: Stripe signature required (`STRIPE_WEBHOOK_SECRET`)
- **Handled events** (and why they matter):
  - `checkout.session.completed`: initial plan selection confirmation (captures customer + subscription)
  - `customer.subscription.created`: subscription created (initial state)
  - `customer.subscription.updated`: upgrades/downgrades/cancel-at-period-end changes
  - `customer.subscription.deleted`: cancellation/termination

---

## Nutrition + image-based food logging status

### Tiered nutrition resolver (implemented)
Purpose: Alfred can resolve calories/macros beyond the school restaurant DB.
- **Core service**: `services/nutrition/resolver.py`
- **Providers**: `services/nutrition/providers.py`
  - USDA FoodData Central
  - Open Food Facts
  - Nutritionix scaffold (optional)
- **Cache**: `nutrition_cache` via `data/nutrition_cache_repository.py`

### Dashboard image uploads + OpenAI Vision (implemented)
Purpose: users can upload a photo (label/receipt/food) from dashboard, extract structured info, and create food logs.
- **Upload metadata table**: `food_image_uploads`
- **Food log metadata**: `food_log_metadata`
- **Schema**: `supabase_schema_nutrition_pipeline.sql`
- **Vision client**: `services/vision/openai_vision.py`
- **Routes**: in `web/routes.py` under dashboard API image endpoints
- **Safety**: vision prompt includes PII redaction guardrails

---

## Image upload pipeline: exact endpoints + lifecycle

These are dashboard-only (not MMS) and are designed to support label/receipt/food recognition.

### 1) Upload an image
- **Route**: `POST /dashboard/api/upload/image`
- **Expected**: multipart form upload
- **Effect**:
  - stores image in Supabase Storage bucket
  - writes a row to `food_image_uploads` with metadata (user, path, status)

### 2) Process an uploaded image into food logs
- **Route**: `POST /dashboard/api/food/image/process`
- **Effect**:
  - fetches the uploaded image from storage
  - runs OpenAI vision extraction to structured nutrition/food items
  - creates `food_logs` entries
  - creates `food_log_metadata` rows linking the logs to the source + confidence

### 3) Delete an uploaded image
- **Route**: `POST /dashboard/api/upload/image/delete`
- **Effect**:
  - deletes the object from storage
  - updates/deletes corresponding `food_image_uploads` record (depending on implementation)

### Operational notes
- The upload limit is controlled by env (`FOOD_IMAGE_MAX_BYTES`) and server-side validation.
- For production, ensure:
  - the bucket exists
  - the service role key is used server-side
  - RLS/storage policies allow the server to read/write objects for the user flow

---

## Data + analytics infrastructure (current)

### Supabase tables actively used (high-level)
Core logs:
- `food_logs`
- `water_logs`
- `gym_logs`
- `sleep_logs`
- `reminders_todos`

Trends:
- Series endpoint computes daily stats via `DashboardData.get_date_stats()`
- Activity endpoint pulls raw entries across tables and filters by metric

Stripe:
- billing columns on `users` (migration: `supabase_schema_stripe_billing.sql`)

Nutrition pipeline:
- `nutrition_cache`
- `food_log_metadata`
- `food_image_uploads`

---

## Trends: how chart + activity log are computed

### Chart series endpoint
- **Route**: `GET /dashboard/api/trends/series?timeframe=...&metric=...`
- **Timeframes**:
  - `7d`: daily points for last 7 days
  - `14d`: daily points for last 14 days
  - `1m`: daily points for last ~30 days
  - `1y`: monthly points (aggregated)
- **Metrics (high-level mapping)**:
  - `calories`, `protein`, `carbs`, `fat`: sums from `food_logs`
  - `water`: sum from `water_logs`
  - `sleep`: `sleep_logs.duration_hours` (note: stored as a single log per day in current repo semantics)
  - `workouts`: count and/or calories (depends on what’s stored in `gym_logs`)
  - `todos`: completed count from `reminders_todos` (or equivalent)
  - `messages`: messages sent count (if/when stored; currently displayed as a metric option)

### Activity log endpoint
- **Route**: `GET /dashboard/api/trends/activity?timeframe=...&metric=...`
- **Output**: a list of event cards with date/time/source and the value relevant to the metric.
- **Important**: server filters events by metric so the log matches the selected metric buttons.

### Numeric correctness note (already fixed)
Supabase sometimes returns numeric columns as strings. `DashboardData.get_date_stats()` now safely coerces values to floats before summing, and handles `sleep_log` as a dict/None (not a list).

---

## Required Supabase migrations (what should be applied)

At minimum, production should include:
- `supabase_schema_complete.sql` (baseline tables)
- `supabase_schema_nutrition_pipeline.sql` (nutrition cache + metadata + uploads)
- `supabase_schema_onboarding_prefs.sql` / `supabase_schema_phase6_additions.sql` (prefs fields; depends on your history)
- `supabase_schema_stripe_billing.sql` (Stripe billing columns)

If your live DB already contains these changes, re-running `IF NOT EXISTS` migrations is safe.

---

## Supabase schema: what the new tables/columns are for (detailed)

### `nutrition_cache`
Used to cache external nutrition lookups so repeated foods don’t re-hit external APIs.
- Key concepts: normalized query, provider, external ID, macronutrient payload, timestamps/TTL semantics.

### `food_log_metadata`
Used to attach “how we got this data” to each created food log.
- Typical fields: `source` (school_db/usda/off/openai_vision/manual), `confidence`, `raw_label`, `provider_ref`.

### `food_image_uploads`
Tracks each uploaded image’s lifecycle and status.
- Typical fields: storage path, original filename, size, created timestamp, processing status/error.

### `users` billing columns (Stripe)
Used to store billing state “as columns on users” (as requested) so the app can render plan badges and later enforce feature gating without joining other tables.

---

## Required environment variables (by feature)

### Required for basic app
- `SUPABASE_URL`
- `SUPABASE_KEY` (service role recommended for server)
- `FLASK_SECRET_KEY`
- `DASHBOARD_PASSWORD` (if used)

### Required for OpenAI + nutrition
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional)
- `OPENAI_VISION_MODEL` (optional)
- `USDA_FDC_API_KEY` (optional but recommended)
- `OPENFOODFACTS_BASE_URL` (optional; usually `https://world.openfoodfacts.org`)
- `NUTRITIONIX_APP_ID` / `NUTRITIONIX_API_KEY` (optional)

### Required for dashboard image uploads
- `FOOD_IMAGE_BUCKET`
- `FOOD_IMAGE_MAX_BYTES`

### Required for Stripe billing
- `BASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_CORE_MONTHLY`
- `STRIPE_PRICE_CORE_ANNUAL`
- `STRIPE_PRICE_PRO_MONTHLY`
- `STRIPE_PRICE_PRO_ANNUAL`

---

## Local development runbook (exact, practical)

### 1) Create + activate venv (macOS)
- Create venv: `python3 -m venv .venv`
- Activate: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

### 2) Configure `.env`
- Start from: `config/env_template.txt`
- Make sure env formatting is `KEY=value` (no spaces around `=`)

### 3) Run the web app
- Start: `python app.py`
- Visit: `http://localhost:5001` (or the configured port)

### 4) Stripe webhook (local)
- Run: `stripe listen --forward-to localhost:5001/stripe/webhook`
- Put the displayed webhook secret into `.env` as `STRIPE_WEBHOOK_SECRET`

---

## Common troubleshooting (high-signal)

### Stripe checkout fails with “No such price: 'prod_...'”
- Root cause: using **Product ID** instead of **Price ID**
- Fix: update env vars `STRIPE_PRICE_*` to `price_...` values, restart app.

### Trends chart shows zeros but activity log has entries
- Typical causes:
  - food logs exist but macro fields are null/empty
  - older rows have strings/nulls in numeric fields (mitigated by safe coercion in `get_date_stats()`)

### Integrations page has no connect buttons
- This is intentional right now (everything is under “Coming Soon”).
- OAuth/sync routes exist; enabling UI is a product step.

---

## Known intentional gaps (by design)

### Integrations
- OAuth + sync routes exist, but the dashboard Integrations UI is currently “Coming Soon”.
- Next step is product decision + UI enabling + credential configuration + testing.

### Password reset
- Settings modal is **UI only**; actual reset email flow via Supabase is not integrated in the dashboard UI.
- Legacy reset routes exist but are not the preferred UX.

### Plan enforcement (entitlements)
- Stripe updates the plan in `users`, and the pricing page displays it.
- The rest of the app does not yet enforce limits/entitlements based on `plan`.

---

## Testing status (practical)

### Verified manually (as of this update)
- Stripe Checkout (test mode) succeeds and webhook updates `public.users`
- Trends activity log and chart endpoints return real data and render
- Pricing page plan badge renders based on `user.plan`

### Still recommended to test
- Image upload pipeline end-to-end in prod (bucket, signed URLs, OpenAI vision)
- Rate limiter behavior under real traffic (image endpoints)
- Background jobs (scheduler) in production environment

---

## Key files (where to look)

### Web + routes
- `web/routes.py` — main dashboard routes + API endpoints + Stripe + trends endpoints
- `web/dashboard.py` — daily stats aggregation + trends computations
- `web/integrations.py` — integration OAuth routes (even if UI is “Coming Soon”)

### Templates
- `templates/dashboard/pricing.html` — pricing UI + checkout JS + current plan badge
- `templates/dashboard/trends.html` — chart + metric UI + activity log
- `templates/dashboard/preferences.html` — redesigned preferences UI
- `templates/dashboard/settings.html` — redesigned settings UI

### Styling
- `static/dashboard/style.css` — unified black/white theme + component styles

### Stripe + migrations
- `stripe.md` — checklist to configure Stripe
- `supabase_schema_stripe_billing.sql` — users columns for billing state

---

## Next recommended roadmap (short)

### 1) Plan enforcement
- Use `users.plan`/`plan_interval` to enforce Free limitations and unlock Core/Pro features.

### 2) Integrations rollout
- Decide which integration becomes “Available” first.
- Re-enable connect buttons and finalize OAuth config + sync verification.

### 3) Trends improvements
- Improve series performance for `1y` if needed (server-side aggregation query instead of per-day loop).
- Add richer activity metadata (source, confidence for food logs from `food_log_metadata`).
