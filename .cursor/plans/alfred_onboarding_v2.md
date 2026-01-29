# Alfred Onboarding v2: Two Paths + Natural Onboarding

## 1. Two Entry Paths

| Path | When | What we do |
|------|------|------------|
| **Text-first (no account)** | Phone **not** in DB | Do **not** create a user. Send intro + signup link. Stop. |
| **Account-first** | Phone **in** DB (signed up on web) | Run **onboarding** (personalized questions). Then normal Alfred. |

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

---

### 3.1 Data We Collect in Onboarding

| Data | Source | Notes |
|------|--------|--------|
| **Reminder style** | Onboarding Q1 | Freeform answer → map to ~10 buckets; store both raw + bucket |
| **Voice style** | Onboarding Q2 | Freeform answer → map to ~10 buckets; store both raw + bucket |
| **Location** | Device (web) | Geolocation or manual (city/region). Use for weather, etc. Collect during signup or settings, not SMS. |
| **Water bottle size** | Onboarding Q | "How big is your usual water bottle?" — ml or oz; store in ml. Used for "drank a bottle." |
| **Morning check-in time** | Onboarding Q | When to send daily morning text (reminders/todos, weather, quote). User can customize what's included later. |

---

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

---

### 3.3 Onboarding Questions (Rewritten)

**Question 1 — Reminder / usage style**

> "How much do you want me in your ear? Some people like constant check-ins and follow-ups; others only want a nudge when it really matters. However you'd describe it—tell me."

- Freeform → map to reminder-style buckets. Store raw + bucket.

**Question 2 — Tone / voice**

> "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."

- Freeform → map to voice-style buckets. Store raw + bucket.

**Question 3 — Water bottle size**

> "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"

- Parse to ml; store `water_bottle_ml`. Use for "drank a bottle," "drank 2 bottles," etc. Fallback to config default if unparseable.

**Question 4 — Morning check-in time**

> "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."

- Parse to hour (0–23) in user's timezone; store `morning_checkin_hour`. Scheduler/notification service uses this instead of global `MORNING_CHECKIN_HOUR`. Mentioning "mix and match later" sets expectation that we'll support toggles (reminders on/off, weather on/off, quote on/off) via natural language later.

---

### 3.4 Location (Device)

- **Where:** Web (signup or settings). Not SMS.
- **How:** Browser geolocation, or manual "City / region" (or ZIP). Store e.g. `location` (text) or `lat`/`lon` + `location_name`.
- **Use:** Weather in check-ins, future location-aware features.

---

### 3.5 Full Onboarding Script (Alfred’s Lines)

| Step | Alfred says |
|------|-------------|
| **0 – Welcome** | "Hey {name}! Good to hear from you. Let me ask you a couple things so I can be useful right away." |
| **1 – Reminder style** | "How much do you want me in your ear? Some people like constant check-ins and follow-ups; others only want a nudge when it really matters. However you'd describe it—tell me." |
| **2 – Voice style** | "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it." |
| **3 – Water bottle** | "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)" |
| **4 – Morning check-in** | "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me." |
| **5 – Done** | "All set. I'll keep that in mind. Text me anything—try 'remind me to call Mom at 5' or 'drank a bottle.' Say 'help' whenever you need it." |

- Use **name** from user record. Keep messages SMS-friendly; split if needed.

---

## 4. What We Store (Schema)

**Users table (or user_preferences):**

- `onboarding_complete` (bool, default false)
- `reminder_style_raw` (text), `reminder_style_bucket` (enum/varchar)
- `voice_style_raw` (text), `voice_style_bucket` (enum/varchar)
- `water_bottle_ml` (int) — used when parsing "drank a bottle"
- `morning_checkin_hour` (int, 0–23) — when to send daily morning text (user timezone)
- `location` or `location_name` (text), optionally `lat`/`lon` — from device on web

**Location:** Filled on web (signup/settings). Rest filled during SMS onboarding.

**Morning message content (later):** Toggles for reminders/todos, weather, quote. User can "mix and match" via natural language ("don't include weather," "add a quote," etc.). Not collected in onboarding—default to all three, customize later.

---

## 5. When Onboarding Runs vs Normal Flow

1. **STOP / HELP** — Handle first; no user creation, no onboarding.
2. **Look up by phone.** If **not in DB** → intro + link, return. **Do not create user.**
3. **In DB, `!onboarding_complete`** → onboarding. Session: `onboarding_step`, `onboarding_data`. Steps 0–5. Parse reply, update user, send next message, return.
4. **In DB, `onboarding_complete`** → normal flow (NLP, handlers).

---

## 6. Code Touchpoints

| Area | Changes |
|------|--------|
| **Processor / webhook** | STOP/HELP first. Unknown phone → intro + link. Known user, !onboarding_complete → onboarding. |
| **User creation** | Only via signup. Never create user from SMS for unknown numbers. |
| **Onboarding module** | Steps 0–5. Parse freeform → buckets (reminder, voice); parse water bottle → ml; parse morning time → hour. Persist raw + bucket + `water_bottle_ml` + `morning_checkin_hour`. |
| **Parser / water handler** | Use **per-user** `water_bottle_ml` when available (else config default) for "drank a bottle." |
| **Scheduler / notification service** | Use **per-user** `morning_checkin_hour` + timezone for morning check-in (replace global `MORNING_CHECKIN_HOUR` where applicable). |
| **Schema** | Add columns above. Migration. |
| **Signup / settings (web)** | Add **timezone**; add **location** (device geolocation or manual). |

---

## 7. Other User-Dependent Options (Beyond Current Onboarding)

Ideas we could add now or later:

| Option | What | Where to collect | Notes |
|--------|------|------------------|--------|
| **Daily water goal** | Default target (e.g. 2L, 8 glasses) | Onboarding or settings | Config has `DEFAULT_WATER_GOAL_ML`. Per-user default would override. Use for "bottles to goal" etc. |
| **Quiet hours** | When not to text (e.g. 10pm–7am) | Settings or onboarding | Store `quiet_hours_start`, `quiet_hours_end`. Nudges/check-ins respect these. |
| **Weekly digest** | Day + time for weekly summary | Settings | Config has `WEEKLY_DIGEST_DAY` / `HOUR`. Per-user override. |
| **Units** | Metric (ml, kg) vs US (oz, lbs) | Onboarding or settings | Affects how we display amounts in replies. |
| **Morning message toggles** | Include reminders? weather? quote? | Natural language later | "Mix and match" — user says "no weather in my morning text," "add a quote," etc. Default: all on. |

**In onboarding now:** reminder style, voice style, water bottle, morning check-in time. **Defer unless we want more:** water goal, quiet hours, weekly digest, units. **Later via natural language:** morning message content toggles.

---

## 8. Deferred

- Exact bucket definitions and mapping rules (refine during implementation).
- "Skip" / "don’t care" / invalid input handling.
- Using `reminder_style_bucket` and `voice_style_bucket` in reminder frequency and response tone.
- Per-user morning check-in scheduling (scheduler today is global; we'll need per-user jobs or a lookup).

---

## 9. Summary

- **Text-first:** Intro + link only. No user created.
- **Account-first:** Onboarding with Q1 (reminder style), Q2 (voice style), Q3 (water bottle), Q4 (morning check-in time), then Done. Freeform → ~10 buckets each for reminder + voice; store raw + bucket. Water bottle → ml. Morning time → hour (0–23).
- **Location:** From device on web (signup/settings). Not in SMS onboarding.
- **Schema:** `onboarding_complete`, reminder/voice raw+bucket, `water_bottle_ml`, `morning_checkin_hour`, location fields.
- **Later:** Morning message toggles (reminders/weather/quote) via natural language; other options (water goal, quiet hours, units, weekly digest) as needed.
