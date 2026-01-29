---
name: Alfred Onboarding & User Preferences
overview: "Two-path onboarding (text-first vs account-first), natural onboarding questions (reminder style, voice style, water bottle, morning check-in), plus user preferences: quiet hours, weekly digest, daily water/macro goals, units, and morning message toggles. All content from alfred_onboarding_v2.md; adds implementation plans for the preference features."
todos:
  - id: onboard-1
    content: "Schema migration: onboarding_complete, reminder/voice raw+bucket, water_bottle_ml, morning_checkin_hour; ensure user_preferences used for quiet hours, units, etc."
    status: pending
  - id: onboard-2
    content: "Processor/webhook: STOP/HELP first; unknown phone → intro + signup link (no user creation); known user !onboarding_complete → onboarding"
    status: pending
  - id: onboard-3
    content: "Onboarding module: steps 0–5 (welcome, reminder style, voice style, water bottle, morning check-in, done); freeform→buckets; persist to user"
    status: pending
  - id: onboard-4
    content: "Signup/settings (web): timezone, location (device geolocation or manual)"
    status: pending
  - id: prefs-1
    content: "Quiet hours: use user_preferences.quiet_hours_start/end; respect in nudges, morning check-in, weekly digest; add UI/settings"
    status: pending
  - id: prefs-2
    content: "Weekly digest: per-user day + hour; scheduler uses user prefs instead of global WEEKLY_DIGEST_DAY/HOUR"
    status: pending
  - id: prefs-3
    content: "Daily water + macro goals: default_water_goal_ml, default_calories/protein/carbs/fat goals; onboarding or settings; use in stats/nudges"
    status: pending
  - id: prefs-4
    content: "Units: user_preferences.units (metric/imperial); use in responses (ml vs oz, kg vs lbs)"
    status: pending
  - id: prefs-5
    content: "Morning message toggles: include_reminders, include_weather, include_quote; natural-language updates; default all on"
    status: pending
isProject: false
---

# Alfred Onboarding & User Preferences

This plan merges [alfred_onboarding_v2.md](alfred_onboarding_v2.md) and adds implementation plans for **quiet hours**, **weekly digest**, **daily water/macro goals**, **units**, and **morning message toggles**.

---

## 1. Two Entry Paths


| Path                        | When                               | What we do                                                       |
| --------------------------- | ---------------------------------- | ---------------------------------------------------------------- |
| **Text-first (no account)** | Phone **not** in DB                | Do **not** create a user. Send intro + signup link. Stop.        |
| **Account-first**           | Phone **in** DB (signed up on web) | Run **onboarding** (personalized questions). Then normal Alfred. |


**Landing:** "Text me!" CTA with Twilio number. Users either text first → intro → sign up → text again, or sign up first → text → onboarding.

---

## 2. Intro Message (Text-First, No Account)

**Draft:**

> "Hey! You're not signed up yet. Alfred works best when we're connected—create an account at [link], then text this number again and we'll get you set up."

- **Link:** Base URL (landing/signup). One message only.

---

## 3. Onboarding (Account-First Only)

**When:** Phone in DB and `onboarding_complete` is false.

**From account/device:** Name, phone (we have). Timezone: add to signup/settings or infer from device. **Location:** get from device on web (geolocation or manual input), store in user. **Water bottle:** we ask in onboarding (below).

### 3.1 Data We Collect in Onboarding


| Data                      | Source        | Notes                                                                                                        |
| ------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------ |
| **Reminder style**        | Onboarding Q1 | Freeform answer → map to ~10 buckets; store both raw + bucket                                                |
| **Voice style**           | Onboarding Q2 | Freeform answer → map to ~10 buckets; store both raw + bucket                                                |
| **Location**              | Device (web)  | Geolocation or manual (city/region). Use for weather, etc. Collect during signup or settings, not SMS.       |
| **Water bottle size**     | Onboarding Q3 | "How big is your usual water bottle?" — ml or oz; store in ml. Used for "drank a bottle."                    |
| **Morning check-in time** | Onboarding Q4 | When to send daily morning text (reminders/todos, weather, quote). User can customize what's included later. |


### 3.2 Reminder Style & Voice Style: Freeform + Buckets

**Goal:** Maximize versatility. Users answer in their own words; we map to ~10 buckets for logic (e.g. nudge frequency, response tone), and keep the raw answer for later use.

**Reminder-style buckets (example):**  
`very_persistent` | `persistent` | `moderate_high` | `moderate` | `moderate_low` | `relaxed` | `very_relaxed` | `minimal` | `only_critical` | `other`

- **Store:** `reminder_style_raw` (text), `reminder_style_bucket` (enum).
- **Mapping:** Keyword/heuristic rules (or simple NLP) map freeform → bucket. Ambiguous → `other`.

**Voice-style buckets (example):**  
`very_casual` | `casual` | `friendly_casual` | `neutral` | `friendly_polished` | `professional` | `polished` | `formal` | `very_formal` | `other`

- **Store:** `voice_style_raw` (text), `voice_style_bucket` (enum).
- **Mapping:** Same idea. Refine buckets during implementation.

### 3.3 Onboarding Questions

**Q1 — Reminder / usage style:**  
"How much do you want me in your ear? Some people like constant check-ins and follow-ups; others only want a nudge when it really matters. However you'd describe it—tell me."

**Q2 — Tone / voice:**  
"How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."

**Q3 — Water bottle size:**  
"How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"

**Q4 — Morning check-in time:**  
"What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."

### 3.4 Location (Device)

- **Where:** Web (signup or settings). Not SMS.
- **How:** Browser geolocation, or manual "City / region" (or ZIP). Store e.g. `location` (text) or `lat`/`lon` + `location_name`.
- **Use:** Weather in check-ins, future location-aware features.

### 3.5 Full Onboarding Script (Alfred's Lines)


| Step                     | Alfred says                                                                                                                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0 – Welcome**          | "Hey {name}! Good to hear from you. Let me ask you a couple things so I can be useful right away."                                                                                                        |
| **1 – Reminder style**   | "How much do you want me in your ear? Some people like constant check-ins and follow-ups; others only want a nudge when it really matters. However you'd describe it—tell me."                            |
| **2 – Voice style**      | "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."                                                          |
| **3 – Water bottle**     | "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"                                                                                                            |
| **4 – Morning check-in** | "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me." |
| **5 – Done**             | "All set. I'll keep that in mind. Text me anything—try 'remind me to call Mom at 5' or 'drank a bottle.' Say 'help' whenever you need it."                                                                |


Use **name** from user record. Keep messages SMS-friendly; split if needed.

---

## 4. Schema (Onboarding + Preferences)

**Users table:**

- `onboarding_complete` (bool, default false)
- `reminder_style_raw` (text), `reminder_style_bucket` (enum/varchar)
- `voice_style_raw` (text), `voice_style_bucket` (enum/varchar)
- `water_bottle_ml` (int) — "drank a bottle"
- `morning_checkin_hour` (int, 0–23) — user timezone
- `location` / `location_name` (text), optionally `lat`/`lon`

**user_preferences** (existing; use or extend):

- `quiet_hours_start` (int, 0–23), `quiet_hours_end` (int, 0–23) — already in schema
- `units` (metric | imperial) — already in schema
- **Add if missing:** `default_water_goal_ml`, `default_calories_goal`, `default_protein_goal`, `default_carbs_goal`, `default_fat_goal`
- **Add:** `weekly_digest_day` (0–6), `weekly_digest_hour` (0–23)
- **Add:** `morning_include_reminders` (bool), `morning_include_weather` (bool), `morning_include_quote` (bool) — default all true

**water_goals:** Per-day overrides remain. `default_water_goal_ml` used when no row for date.

---

## 5. When Onboarding Runs vs Normal Flow

1. **STOP / HELP** — Handle first; no user creation, no onboarding.
2. **Look up by phone.** If **not in DB** → intro + link, return. **Do not create user.**
3. **In DB, `!onboarding_complete**` → onboarding. Session: `onboarding_step`, `onboarding_data`. Steps 0–5. Parse reply, update user, send next message, return.
4. **In DB, `onboarding_complete**` → normal flow (NLP, handlers).

---

## 6. Code Touchpoints (Onboarding)


| Area                                 | Changes                                                                                                   |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| **Processor / webhook**              | STOP/HELP first. Unknown phone → intro + link. Known user, !onboarding_complete → onboarding.             |
| **User creation**                    | Only via signup. Never create user from SMS for unknown numbers.                                          |
| **Onboarding module**                | Steps 0–5. Parse freeform → buckets; parse water bottle → ml; parse morning time → hour. Persist to user. |
| **Parser / water handler**           | Per-user `water_bottle_ml` when available (else config default).                                          |
| **Scheduler / notification service** | Per-user `morning_checkin_hour` + timezone for morning check-in.                                          |
| **Signup / settings (web)**          | Timezone; location (device geolocation or manual).                                                        |


---

## 7. Deferred (Onboarding)

- Exact bucket definitions and mapping rules.
- "Skip" / "don't care" / invalid input handling.
- Using `reminder_style_bucket` and `voice_style_bucket` in reminder frequency and response tone.
- Per-user morning check-in scheduling (scheduler today is global; per-user jobs or lookup needed).

---

## 8. Summary (Onboarding)

- **Text-first:** Intro + link only. No user created.
- **Account-first:** Onboarding Q1–Q4 (reminder style, voice style, water bottle, morning check-in) then Done. Freeform → buckets; store raw + bucket. Water bottle → ml, morning → hour.
- **Location:** From device on web. **Schema:** onboarding fields on users; preferences (including new ones below) in `user_preferences` or users.

---

## 9. Plans for: Quiet Hours, Weekly Digest, Daily Goals, Units, Morning Toggles

### 9.1 Quiet Hours

**What:** Time window when we don't send nudges, morning check-in, or other non-urgent messages (e.g. 10pm–8am).

**Schema:** `user_preferences.quiet_hours_start`, `quiet_hours_end` (0–23). Already in schema.

**Where we collect:** Settings (web) or optionally onboarding. Could add an onboarding question: "When should I avoid texting you? (e.g. 10pm–7am)" and parse to start/end.

**Code touchpoints:**

- **Notification service / reminder service / scheduler:** Before sending morning check-in, nudges, weekly digest, or reminder follow-ups, check user's current time in their timezone against `quiet_hours_start`/`quiet_hours_end`. If inside window, skip send (or queue for later).
- **Settings UI:** Form to set quiet hours (e.g. two time inputs or "10pm – 7am" single field); save to `user_preferences`.

**Edge cases:** Window crossing midnight (e.g. 22–8). Store as start < end normally; if start > end, treat as "overnight" (e.g. 22–8 = 10pm to 8am).

---

### 9.2 Weekly Digest

**What:** Per-user day and hour for the weekly summary (e.g. Monday 8pm). Content: water averages, food/gym highlights, task completion, etc.

**Schema:** Add to `user_preferences`: `weekly_digest_day` (0=Monday … 6=Sunday), `weekly_digest_hour` (0–23). Default from config (`WEEKLY_DIGEST_DAY`, `WEEKLY_DIGEST_HOUR`) for existing users.

**Where we collect:** Settings (web). Optional onboarding Q: "What day and time do you want your weekly summary?" (e.g. "Monday 8pm").

**Code touchpoints:**

- **Scheduler:** Weekly digest job currently uses global `WEEKLY_DIGEST_DAY` / `WOUR`. Change to **per-user**: iterate users who have digest enabled, check each user's `weekly_digest_day` / `weekly_digest_hour` and timezone, send only when it's that local day/hour for them.
- **Notification service:** `_send_weekly_digest` (or equivalent) already segments by user; ensure it uses `user_preferences` for day/hour.
- **Settings UI:** Dropdown for day, time picker for hour; save to `user_preferences`.

---

### 9.3 Daily Water + Macro Goals

**What:** Per-user **default** daily targets:

- **Water:** `default_water_goal_ml`. Used when no `water_goals` row for that date; for "bottles to goal," progress messages, nudges.
- **Macros:** `default_calories_goal`, `default_protein_goal`, `default_carbs_goal`, `default_fat_goal` (grams). Used for "how am I doing today?" type replies, progress in stats, and optional nudges (e.g. "you're 200 cal over your usual target").

**Schema:** Add to `user_preferences` (or users if you prefer):

- `default_water_goal_ml` (int)
- `default_calories_goal` (int), `default_protein_goal` (int), `default_carbs_goal` (int), `default_fat_goal` (int). Allow NULL for "not set."

**Where we collect:** Onboarding and/or settings. Onboarding Q(s): e.g. "What's your daily water goal? (e.g. 2L, 8 glasses)" and "Do you track calories or macros? If so, what are your typical daily targets? (e.g. 2000 cal, 150g protein)" — parse and store. Simpler: just water goal in onboarding; add macro goals in settings.

**Code touchpoints:**

- **Notification service:** Gentle nudges use `default_water_goal_ml` when computing "bottles behind" (replace `DEFAULT_WATER_GOAL_ML` where user-specific).
- **Water repo / dashboard:** Default goal for a given date = `water_goals` row else `user_preferences.default_water_goal_ml` else config default.
- **Query handler / stats / context:** When user asks "how am I doing" or we show food stats, compare today's totals to `default_*_goal` and include progress (e.g. "Calories: 1800/2000; protein 120/150g").
- **Settings UI:** Form for water goal and macro goals; save to `user_preferences`.

---

### 9.4 Units

**What:** User prefers **metric** (ml, kg, etc.) or **imperial** (oz, lbs). Affects how we **display** amounts in SMS replies, dashboard, and digests.

**Schema:** `user_preferences.units` ('metric' | 'imperial'). Already in schema.

**Where we collect:** Onboarding or settings. Onboarding Q: "Do you prefer metric (ml, kg) or US units (oz, lbs)?" Or add to settings only.

**Code touchpoints:**

- **Response formatter / query handler / notification service:** When formatting water ("X ml" vs "X oz"), weight, or other quantities, check `user_preferences.units` and convert/display accordingly. Store internally in metric; convert only for display.
- **Parser:** Continue to accept both (e.g. "16oz" or "500ml"); storage stays metric.
- **Settings UI:** Toggle or dropdown for units; save to `user_preferences`.

---

### 9.5 Morning Message Toggles

**What:** User can turn on/off **reminders & todos**, **weather**, and **motivational quote** in the daily morning text. "Mix and match" — e.g. "no weather," "add a quote," "remove reminders."

**Schema:** Add to `user_preferences` (or users):

- `morning_include_reminders` (bool, default true)
- `morning_include_weather` (bool, default true)
- `morning_include_quote` (bool, default true)

**Where we collect:** **Not** during onboarding (we say "you can mix and match later"). User changes via **natural language** over SMS, e.g.:

- "Don't include weather in my morning text"
- "Add the quote back"
- "No reminders in the morning message"

**Code touchpoints:**

- **Intent / handler:** New or extended intent for "morning message preferences" / "customize morning text." Parse phrases like "no weather," "include quote," "skip reminders" → update `user_preferences` flags.
- **Notification service (morning check-in):** When building the morning message, check the three flags. Omit reminders block if `!morning_include_reminders`, omit weather if `!morning_include_weather`, omit quote if `!morning_include_quote`.
- **Optional:** Settings UI for these toggles as well.

---

## 10. Summary of New Preference Features


| Feature               | Schema                                                               | Collect                                    | Use                                                             |
| --------------------- | -------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------- |
| **Quiet hours**       | `quiet_hours_start` / `_end` (user_preferences)                      | Settings or onboarding                     | Skip nudges, morning check-in, digest, follow-ups during window |
| **Weekly digest**     | `weekly_digest_day` / `_hour` (user_preferences)                     | Settings or onboarding                     | Per-user schedule for weekly summary                            |
| **Daily water goal**  | `default_water_goal_ml` (user_preferences)                           | Onboarding or settings                     | Default when no water_goals row; nudges, "bottles to goal"      |
| **Daily macro goals** | `default_calories_goal`, `_protein_goal`, `_carbs_goal`, `_fat_goal` | Onboarding or settings                     | Stats, "how am I doing," optional nudges                        |
| **Units**             | `units` (user_preferences)                                           | Onboarding or settings                     | Display ml vs oz, kg vs lbs in responses                        |
| **Morning toggles**   | `morning_include_reminders` / `_weather` / `_quote`                  | Natural language (and optionally settings) | Build morning message based on flags                            |


All of the above should be reflected in migrations, repos, and UI as we implement.