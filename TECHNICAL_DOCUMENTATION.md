# Alfred (SMS Assistant) – Technical Documentation

This document describes the technical architecture, data flows, and implementation details of Alfred as of the current state of the codebase. It is intended for developers working on the project or integrating with it.

---

## 1. Project Overview

Alfred is a personalized SMS-first assistant that feels like a real person but is grounded in user data. Users interact via SMS and a web dashboard; Alfred logs food, water, workouts, sleep, todos, and reminders; retrieves history from Supabase; and uses natural language processing (classic pipeline or agent mode) to route intents and execute handlers.

**Core characteristics:**

- **Dual “brains”:** Classic pipeline (intent classification → entity extraction → handler routing) and optional agent mode (OpenAI tool-calling + durable memory).
- **Backend:** Flask app, Supabase (PostgreSQL + Storage), Twilio for SMS.
- **NLP:** Configurable engine (default: OpenAI; fallback: Gemini) for intent/entity; agent mode uses OpenAI (gpt-4o, gpt-4o-mini, embeddings).
- **Nutrition:** Tiered resolver (optional USDA in Supabase, Open Food Facts, Nutritionix) with Supabase caching.
- **Gym:** Exercise data from `data/exercises.csv` (or fallback `data/gym_workouts.json`) for name enrichment.
- **Payments:** Stripe subscriptions (Free/Core/Pro) with billing state on `public.users`.

---

## 2. High-Level Architecture

```
Twilio SMS  →  Flask (/webhook/twilio)  →  Alfred brain  →  TwiML response
                                   |
                                   +→ Supabase (users, logs, memory, billing, cache)
                                   +→ Background jobs (nudges, digests, sync)

Web dashboard  →  Flask (/dashboard/...)  →  Supabase (auth, data, storage)
```

**Message flow:**

1. Incoming SMS hits `/webhook/twilio`; Flask validates Twilio signature and forwards body to the message processor.
2. Processor resolves user by phone (or creates/onboards), loads session and context.
3. Either **classic pipeline** (intent → entities → handler) or **agent mode** (tool-calling orchestration) runs.
4. Handler writes to Supabase (food_logs, water_logs, gym_logs, todos, etc.) and returns a response.
5. Response is formatted for SMS (length, formatting) and sent via Twilio.

---

## 3. Module Layout

| Directory | Purpose |
|-----------|--------|
| **`app.py`** | Flask entrypoint, Twilio webhook routes, service initialization, health endpoints |
| **`core/`** | Message processor, conversation context, session manager, onboarding |
| **`nlp/`** | Intent classification, entity extraction, domain parsers (food, water, gym, etc.), pattern matcher, database loader |
| **`handlers/`** | Intent-specific handlers (food, water, gym, todo, query, integration) |
| **`data/`** | Repository layer for Supabase (users, food, water, gym, todos, knowledge, integrations, nutrition cache, food log metadata, food image uploads, user memory, etc.) |
| **`services/`** | Nutrition resolver, notification/nudge service, reminder service, scheduler, sync service, agent orchestrator + tool executor, vision pipeline |
| **`learning/`** | Pattern extraction, association learning, context analysis, learning orchestrator |
| **`web/`** | Dashboard routes, auth, trends APIs |
| **`integrations/`** | OAuth and sync framework (Fitbit, Google Calendar) |
| **`responses/`** | Response formatting for SMS |

---

## 4. Natural Language Processing

### 4.1 NLP Engine Selection

- **Config:** `NLP_ENGINE` in config (from env: `openai` or `gemini`). Default is **OpenAI**.
- **Usage:** Intent classification and entity extraction use the selected engine (OpenAI or Gemini client in `nlp/`).
- **Agent mode:** Always uses OpenAI (gpt-4o for voice, gpt-4o-mini for routing/summarization, text-embedding-3-small for memory).

### 4.2 Intent Classification

The `IntentClassifier` maps user messages to intents such as:

- **Logging:** `water_logging`, `food_logging`, `gym_workout`, `sleep_logging`
- **Tasks:** `todo_add`, `reminder_set`, `assignment_add`, `task_complete`
- **Queries:** `stats_query`, `what_should_i_do`, `food_suggestion`
- **Learning:** `fact_storage`, `fact_query`
- **System:** `undo_edit`, `vague_completion`, `integration_manage`, onboarding/system flows

Classification is done via the configured LLM with few-shot prompting.

### 4.3 Entity Extraction

The `EntityExtractor` pulls structured data from text: temporal expressions, quantities (water, weight, reps, sets), food items, exercise names, task metadata, etc.

### 4.4 Domain-Specific Parsing (Parser)

The `Parser` uses the LLM and optional databases for each domain:

**Food:**

- User can provide explicit macros; otherwise the **nutrition resolver** is used.
- **Nutrition resolver** (see Section 6): Tiered lookup (optional USDA Supabase → Open Food Facts → Nutritionix), with results cached in Supabase. No primary “restaurant JSON” database; nutrition is resolved by query.
- Parsed output: food name, calories, protein, carbs, fat, restaurant, portion multiplier, nutrition source/confidence.

**Water:**

- Multi-unit support (ml, oz, liters, bottles). Bottle size from config (`WATER_BOTTLE_SIZE_ML`) or database loader.
- Implicit quantities (e.g. “drank a bottle” → default ml).

**Gym:**

- Exercise names, sets, reps, weight parsed from formats like “135x5”, “3 sets of 5 at 225”.
- **Exercise database:** Enrichment (primary_muscle, secondary_muscles, exercise_type, muscle_group) comes from the **gym database** provided by `DatabaseLoader.get_gym_database()` (see Section 5.2).
- Database is populated from **`data/exercises.csv`** if present, else **`data/gym_workouts.json`**.

**Temporal:**

- Relative and absolute times; timezone-aware handling (UTC storage, user timezone for display).

### 4.5 Pattern Matching and Learning

- **PatternMatcher:** Applies user-specific learned patterns before NLP (e.g. “dhamaka” → gym_workout).
- **LearningOrchestrator:** Applies patterns, extracts new ones from messages, persists to `KnowledgeRepository`, updates confidence on usage.
- Patterns live in `user_knowledge` (per user).

---

## 5. Gym / Exercise Data

### 5.1 Source of Truth: exercises.csv

- **Primary source:** `data/exercises.csv` (tracked in git; see `.gitignore` for `!data/exercises.csv`).
- **Origin:** Built from **wger** (public API) and **MuscleWiki** (unofficial export). A one-off script merged and deduplicated by exercise name; that script has been removed. The CSV is the canonical exercise list.
- **Approximate size:** ~1,379 unique exercises (after merging duplicates from both sources).

### 5.2 CSV Schema (High Level)

Each row has (among others): `exerciseId`, `name`, `equipments`, `bodyParts`, `exerciseType`, `targetMuscles`, `secondaryMuscles`, `keywords`, `overview`, `instructions`, `exerciseTips`, `variations`, `relatedExerciseIds`, `source`. List fields are stored as JSON strings in cells.

### 5.3 How the App Uses It

- **Config:** `EXERCISES_CSV_PATH` points to `data/exercises.csv`. `GYM_DATABASE_PATH` points to `data/gym_workouts.json` (fallback).
- **DatabaseLoader** (`nlp/database_loader.py`):
  - `get_gym_database()`: Prefers CSV. If `EXERCISES_CSV_PATH` exists, calls `_load_and_flatten_csv()`; otherwise loads `gym_workouts.json` and flattens it.
  - **Flattened shape:** A dict keyed by normalized exercise name (and variations): each value is `{ "primary_muscle", "secondary_muscles", "exercise_type", "muscle_group" }`. Used by the parser to enrich parsed gym exercises.
- **Parser** (`nlp/parser.py`): In `parse_gym_workout()`, after LLM extraction, matches exercise names to the flattened DB and attaches `primary_muscle`, `secondary_muscles`, `exercise_type`, and optionally sets `muscle_group` on the workout.

---

## 6. Nutrition Pipeline

### 6.1 Tiered Resolver

Nutrition for food logging (when user doesn’t supply macros) is resolved by:

1. **Cache:** `NutritionCacheRepository` checks Supabase `nutrition_cache` by normalized query + optional restaurant.
2. **Providers (in order):**
   - **USDA Supabase** (optional): If `USE_USDA_SUPABASE` is not `false` and Supabase is configured, `USDASupabaseProvider` queries `usda_food`, `usda_food_nutrient`, `usda_nutrient`, etc. If USDA tables have been dropped, set `USE_USDA_SUPABASE=false` to skip this provider and avoid errors.
   - **Open Food Facts:** Public API; no key required.
   - **Nutritionix:** Requires `NUTRITIONIX_APP_ID` and `NUTRITIONIX_API_KEY`.
3. **Cache write-back:** Successful result is stored in `nutrition_cache` with configurable TTL (`NUTRITION_CACHE_TTL_DAYS`).

**Key code:** `services/nutrition/resolver.py`, `services/nutrition/providers.py`, `data/nutrition_cache_repository.py`.

### 6.2 USDA in Supabase (Optional)

- **Purpose:** Local USDA FoodData Central data for fast, offline-capable macro lookup.
- **When used:** Only if `USE_USDA_SUPABASE` is not set to `false` and the USDA tables exist in Supabase.
- **Schema:** `supabase_schema_usda.sql` defines tables (e.g. `usda_food`, `usda_food_nutrient`, `usda_nutrient`, `usda_food_portion`, `usda_measure_unit`, `usda_food_category`, `usda_branded_food`). Data is imported from the official USDA CSVs (or from `data/USDA/` if you have them).
- **Removing USDA:** Run `supabase_drop_usda.sql` in the Supabase SQL editor to drop all USDA tables. Then set `USE_USDA_SUPABASE=false` in `.env` so the app skips the USDA provider. Nutrition continues via Open Food Facts and Nutritionix.
- **Docs:** `data/FOOD_DATABASE_GUIDE.md` describes the food/nutrition data setup.

### 6.3 Food Log Metadata and Image Uploads

- **Food log metadata:** When nutrition is resolved, source and confidence can be stored via `FoodLogMetadataRepository` (e.g. `food_log_metadata` table).
- **Image uploads:** Dashboard can upload food/label/receipt images. Stored in Supabase Storage (bucket from `FOOD_IMAGE_BUCKET`); metadata in `food_image_uploads`. Vision pipeline can process these to structured logs (see `services/vision/`).

---

## 7. Data Layer (Repositories)

### 7.1 Pattern

- **Base:** `BaseRepository` in `data/base_repository.py` provides common Supabase CRUD and query building.
- **Convention:** One repository per entity/table; domain methods (e.g. `get_by_date`, `get_by_date_range`) in addition to base methods.

### 7.2 Repositories (Summary)

| Repository | Table / concern | Main use |
|------------|-----------------|----------|
| UserRepository | users | Auth, phone/email lookup, onboarding state |
| FoodRepository | food_logs | Create/list food logs, macros |
| WaterRepository | water_logs | Daily water, goals |
| GymRepository | gym_logs | Workout logs by date/range/exercise |
| TodoRepository | todos, reminders | Todos and reminders, completion |
| SleepRepository | sleep_logs | Sleep duration, etc. |
| AssignmentRepository | assignments | Academic assignments |
| KnowledgeRepository | user_knowledge | Learned patterns (learning system) |
| IntegrationRepository | integration_connections, sync_history | OAuth connections, sync state |
| NutritionCacheRepository | nutrition_cache | Cache for nutrition resolver |
| FoodLogMetadataRepository | food_log_metadata | Nutrition source/confidence per log |
| FoodImageUploadRepository | food_image_uploads | Dashboard image upload metadata |
| UserPreferencesRepository | user_preferences | Quiet hours, digest, goals, etc. |
| UserMemoryEmbeddingsRepository / UserMemoryItemsRepository / UserMemoryStateRepository | Agent memory tables | Agent mode durable memory |
| UserUsageRepository | user_usage | Usage/analytics if present |
| USDARepository | usda_* tables | Used only by USDASupabaseProvider when USDA is enabled |

### 7.3 Schema and Migrations

- **Baseline:** `supabase_schema_complete.sql` (or equivalent) for core tables.
- **Feature-specific:** e.g. `supabase_schema_onboarding_prefs.sql`, `supabase_schema_nutrition_pipeline.sql`, `supabase_schema_usda.sql`, `supabase_schema_agent_memory.sql`, `supabase_schema_stripe_billing.sql`, etc.
- **USDA teardown:** `supabase_drop_usda.sql` drops all USDA tables when you no longer want them.

---

## 8. Message Processing Engine

### 8.1 Classic Pipeline (MessageProcessor)

1. **User resolution:** Phone → user_id (create user if needed; respect onboarding flow).
2. **Session:** Load or create session (pending confirmations, multi-turn state).
3. **Patterns:** Apply learned patterns (e.g. custom words → intents).
4. **Intent:** Classify with configured NLP engine.
5. **Entities:** Extract entities (dates, amounts, food, exercises, etc.).
6. **Routing:** Select handler by intent (food_logging → FoodHandler, gym_workout → GymHandler, etc.).
7. **Parsing:** Handler uses Parser for domain parsing (e.g. parse_food, parse_gym_workout) which may call nutrition resolver and gym DB.
8. **Execution:** Handler writes to Supabase and returns a response.
9. **Learning:** Optionally extract and store new patterns, update usage.
10. **Format:** Response formatted for SMS (length, line breaks) and returned.

### 8.2 Agent Mode

- **Entry:** When agent mode is enabled, the same incoming message can be routed to the agent orchestrator instead of (or in addition to) the classic pipeline.
- **Implementation:** `services/agent/orchestrator.py`, `services/agent/tool_executor.py`.
- **Models:** OpenAI gpt-4o (user-facing), gpt-4o-mini (routing/summarization), text-embedding-3-small (memory embeddings).
- **Tools:** Validated tools for querying logs, creating todos, etc.; tool results are fed back to the model.
- **Memory:** User memory repositories store and retrieve embeddings/items for durable context.

### 8.3 Context and Session

- **ConversationContext:** Today’s summary (food, water, gym, todos), recent activity, upcoming items. Used by handlers and agent.
- **SessionManager:** Pending confirmations, multi-turn state, timeouts. Stored per user.

---

## 9. Intent Handlers (Classic)

- **FoodHandler:** Uses Parser (nutrition resolver + optional image metadata). Writes to `food_logs` and optionally food log metadata.
- **WaterHandler:** Parser for water amounts; writes to `water_logs`; can use daily goals.
- **GymHandler:** Parser for gym (using gym DB from CSV/JSON); writes to `gym_logs` with exercise, sets, reps, weight.
- **TodoHandler:** Todos and reminders; due dates; completion.
- **QueryHandler:** Stats, “what did I do”, suggestions; reads from multiple repos.
- **IntegrationHandler:** OAuth links, disconnect, manual sync for Fitbit/Google Calendar.

All handlers use the shared Parser, Formatter, and Supabase repos.

---

## 10. Background Jobs

- **Scheduler:** APScheduler; runs reminders, nudges, digests, syncs.
- **ReminderService:** Follow-ups for sent reminders; task decay (stale todo checks).
- **NotificationService:** Gentle nudges (water, gym); weekly digest (averages, completion).
- **SyncService:** Periodic sync of Fitbit/Google data; token refresh; deduplication.

---

## 11. Web Dashboard and Auth

- **Auth:** Registration, login (bcrypt), password reset, phone verification; Flask sessions; optional JWT for API.
- **Dashboard:** Trends, calendar-style views, chat test (same processor as SMS), settings, integrations, pricing (Stripe). Data via Supabase; some routes use `DashboardData` for aggregated stats.
- **Storage:** Food/label/receipt images in Supabase Storage; metadata in `food_image_uploads`.

---

## 12. Integrations

- **Fitbit:** OAuth; sync activities/sleep; webhooks for real-time updates.
- **Google Calendar:** OAuth; fetch events for context/suggestions.
- **Google Fit:** Structure present; implementation can be extended.
- **IntegrationAuthManager:** OAuth flows, token encryption (Fernet), refresh. **SyncManager:** Fetch, map, dedupe, log sync history.

---

## 13. Configuration

Centralized in `config.py` (env via `.env`):

- **Twilio:** Account SID, auth token, phone number.
- **NLP:** `NLP_ENGINE` (openai/gemini), OpenAI/Gemini keys and models; agent uses OpenAI.
- **Supabase:** URL, key.
- **Nutrition:** `USE_USDA_SUPABASE`, Open Food Facts URL, Nutritionix IDs, cache TTL; USDA FDC API key if using API path.
- **Gym:** `EXERCISES_CSV_PATH`, `GYM_DATABASE_PATH`.
- **Water:** Bottle size, default daily goal.
- **Reminders / digest / nudges:** Delays, days, hours, on/off flags.
- **Stripe:** Secret key, webhook secret, price IDs (Core/Pro, monthly/annual).
- **Integrations:** Fitbit/Google client IDs and secrets; base URL for OAuth.
- **App:** Base URL, dashboard password, Flask secret, encryption key; environment and log level.

Validation on startup ensures required Twilio (and any other required) vars are set.

---

## 14. Security

- **Auth:** bcrypt for passwords; secure sessions; CSRF for OAuth; optional account lockout.
- **Data:** RLS on Supabase so users only access their own rows.
- **API:** Twilio webhook signature verification; rate limiting on sensitive routes; no sensitive data in error messages.
- **Secrets:** All in env; no credentials in repo.

---

## 15. Error Handling and Logging

- **Handlers:** Try/except; user-friendly messages; errors logged with context.
- **Nutrition/Gym:** Resolver and DB loader handle missing data (e.g. skip USDA if tables missing when `USE_USDA_SUPABASE=false`); parser continues with empty enrichment if gym DB missing.
- **Logging:** Structured where used; log levels from config.

---

## 16. Deployment

- **Entry:** `app.py` (Flask); health endpoints (e.g. `/health`, `/health/ready`, `/health/live`) for probes.
- **Env:** All config from environment (e.g. Koyeb, Railway, or Docker env).
- **Background jobs:** Run in the same process (APScheduler); graceful shutdown so jobs can finish.
- **Docs:** `DEPLOYMENT.md` for platform-specific steps (e.g. Koyeb).

---

## 17. Technology Stack

- **Backend:** Python 3.x, Flask
- **Database:** Supabase (PostgreSQL, Storage)
- **SMS:** Twilio
- **NLP:** OpenAI (default), Gemini (fallback); agent: OpenAI (gpt-4o, gpt-4o-mini, embeddings)
- **Payments:** Stripe
- **Auth:** bcrypt, Flask sessions, optional JWT
- **Scheduling:** APScheduler
- **Frontend:** HTML/CSS/JS (dashboard)

---

## 18. Summary of Recent / Important Behaviors

- **Gym:** App uses **`data/exercises.csv`** for exercise enrichment; fallback is **`data/gym_workouts.json`**. Config: `EXERCISES_CSV_PATH`, `GYM_DATABASE_PATH`.
- **Nutrition:** **USDA in Supabase is optional.** Set `USE_USDA_SUPABASE=false` if USDA tables are dropped; resolver uses Open Food Facts and Nutritionix. Use **`supabase_drop_usda.sql`** to remove USDA tables.
- **Food:** No primary “restaurant JSON” DB; nutrition comes from the **tiered resolver** (optional USDA → OFF → Nutritionix) and **cache**.
- **Agent mode:** OpenAI-based tool-calling and memory; separate from classic intent handlers.
- **Stripe:** Billing state on `users`; Core/Pro plans; webhook for subscription updates.

---

## 19. Testing and Health

- **Chat interface:** `/dashboard/chat` and `/dashboard/api/chat` use the same MessageProcessor as SMS for testing without Twilio.
- **Health endpoints:** `/health`, `/health/ready`, `/health/live` for liveness/readiness (e.g. Koyeb).
- **Manual job triggers:** Dashboard can trigger background jobs for testing.
- **Tests:** `tests/` and pytest; unit and integration tests for processor, handlers, repos.

---

## 20. Performance and Caching

- **Context:** Conversation context and today’s summary cached per user to reduce DB calls.
- **Nutrition:** Resolver results cached in `nutrition_cache` (TTL from config).
- **Gym DB:** Loaded once per process by DatabaseLoader (CSV or JSON flattened in memory).
- **Patterns:** Learned patterns loaded per user/session where applicable.
- **Supabase:** Indexed queries on user_id, timestamps; connection via Supabase client.

---

## 21. Key File Reference

| Concern | File(s) |
|--------|--------|
| Entrypoint, webhook | `app.py` |
| Message processing | `core/processor.py` |
| Onboarding | `core/onboarding.py` |
| Context, session | `core/context.py`, `core/session.py` |
| Intent, entities, parser | `nlp/intent_classifier.py`, `nlp/entity_extractor.py`, `nlp/parser.py` |
| Gym DB loading | `nlp/database_loader.py` |
| Nutrition resolver | `services/nutrition/resolver.py`, `services/nutrition/providers.py` |
| Handlers | `handlers/food_handler.py`, `handlers/gym_handler.py`, etc. |
| Repositories | `data/*.py` (food_repository, gym_repository, nutrition_cache_repository, etc.) |
| Agent | `services/agent/orchestrator.py`, `services/agent/tool_executor.py` |
| Config | `config.py` |
| USDA schema / drop | `supabase_schema_usda.sql`, `supabase_drop_usda.sql` |
| Food/nutrition setup | `data/FOOD_DATABASE_GUIDE.md` |

---

This technical documentation reflects the architecture and behavior of Alfred as implemented up to the current date.
