# Implementation Phases - Step-by-Step Guide

This document breaks down the massive rebuild into manageable phases. Each phase can be completed independently, with clear deliverables and testing steps.

---

## Overview

**Total Phases:** 8 phases  
**Estimated Time:** Each phase is designed to be completable in 1-2 focused sessions  
**Dependencies:** Each phase builds on previous phases

---

## Phase 0: Pre-Implementation Setup (YOU DO THIS)

**Purpose:** Set up all external services and configurations before coding begins.

### What You Need to Do:

#### 1. Supabase Database Setup
- [ ] Go to [supabase.com](https://supabase.com) and log in
- [ ] Create a new project (or use existing)
- [ ] Go to **SQL Editor**
- [ ] Wait for Phase 1 - I'll provide the complete SQL schema to run

#### 2. Environment Variables Setup
Create/update your `.env` file with these variables:

**Existing (keep these):**
```bash
# Twilio
TWILIO_ACCOUNT_SID=your_existing_value
TWILIO_AUTH_TOKEN=your_existing_value
TWILIO_PHONE_NUMBER=your_existing_value
YOUR_PHONE_NUMBER=your_existing_value

# Gemini
GEMINI_API_KEY=your_existing_value
GEMINI_MODEL=gemini-2.5-flash

# Supabase
SUPABASE_URL=your_existing_value
SUPABASE_KEY=your_existing_value
```

**New (add these for later phases):**
```bash
# Flask Security
FLASK_SECRET_KEY=generate_random_string_here  # Use: python -c "import secrets; print(secrets.token_hex(32))"

# Token Encryption (for OAuth tokens)
ENCRYPTION_KEY=generate_random_string_here  # Use: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Integration OAuth (add when ready for Phase 5)
# FITBIT_CLIENT_ID=will_add_later
# FITBIT_CLIENT_SECRET=will_add_later
# GOOGLE_CLIENT_ID=will_add_later
# GOOGLE_CLIENT_SECRET=will_add_later

# Redis (optional, for caching - add in Phase 3)
# REDIS_URL=redis://localhost:6379

# Email (for password reset - add in Phase 4)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# FROM_EMAIL=your_email@gmail.com

# App Settings
ENVIRONMENT=development  # or 'production'
LOG_LEVEL=INFO
```

**To generate secrets:**
```bash
# Flask Secret Key
python -c "import secrets; print(secrets.token_hex(32))"

# Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 3. Update Requirements
I'll update `requirements.txt` in Phase 1, but you can prepare:
- [ ] Make sure you have Python 3.9+
- [ ] Virtual environment is set up
- [ ] Current dependencies installed

#### 4. Backup Current Code
- [ ] Commit current code to git
- [ ] Create a backup branch: `git checkout -b backup-before-rebuild`
- [ ] Push backup branch: `git push origin backup-before-rebuild`

---

## Phase 1: Foundation & Database Schema

**Goal:** Create the new directory structure and complete database schema.

### What I'll Build:
1. ✅ New directory structure (`core/`, `handlers/`, `data/`, `nlp/`, `learning/`, `services/`, `web/`, `integrations/`, `utils/`, `tests/`)
2. ✅ Complete database schema SQL file (`supabase_schema_complete.sql`)
3. ✅ Updated `requirements.txt` with all new dependencies
4. ✅ Base repository pattern (`data/base_repository.py`)
5. ✅ Updated `config.py` with new configuration variables

### What You Need to Do:

#### 1. Run Database Schema
- [ ] Open Supabase SQL Editor
- [ ] Copy the entire contents of `supabase_schema_complete.sql`
- [ ] Paste and run it
- [ ] Verify all 14 tables were created (check Tables section)
- [ ] Verify RLS policies are enabled (check Authentication > Policies)

#### 2. Install New Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Test Database Connection
I'll create a test script - run it:
```bash
python tests/test_database_connection.py
```

### Deliverables:
- ✅ New directory structure exists
- ✅ Database schema created in Supabase
- ✅ All tables visible in Supabase dashboard
- ✅ Can connect to database from code

### Testing:
- [ ] Run database connection test
- [ ] Verify tables in Supabase dashboard
- [ ] Check RLS policies are active

---

## Phase 2: Data Layer & Repositories

**Goal:** Extract all database operations into repository pattern.

### What I'll Build:
1. ✅ `data/base_repository.py` - Base repository class
2. ✅ `data/user_repository.py` - User account operations
3. ✅ `data/food_repository.py` - Food log operations
4. ✅ `data/water_repository.py` - Water log operations
5. ✅ `data/gym_repository.py` - Gym log operations
6. ✅ `data/todo_repository.py` - Todo/reminder operations
7. ✅ `data/knowledge_repository.py` - Learning patterns storage
8. ✅ Unit tests for repositories

### What You Need to Do:
- [ ] Nothing! This is all code.

### Deliverables:
- ✅ All data operations use repository pattern
- ✅ Old `supabase_database.py` can be deprecated
- ✅ All CRUD operations tested

### Testing:
- [ ] Run repository unit tests: `pytest tests/test_repositories.py`
- [ ] Manually test creating/reading/updating/deleting records via repositories

---

## Phase 3: NLP Layer Refactoring

**Goal:** Split `gemini_nlp.py` into modular components.

### What I'll Build:
1. ✅ `nlp/gemini_client.py` - Gemini API client
2. ✅ `nlp/intent_classifier.py` - Intent classification
3. ✅ `nlp/entity_extractor.py` - Entity extraction
4. ✅ `nlp/parser.py` - Domain-specific parsing (food, gym, etc.)
5. ✅ `nlp/pattern_matcher.py` - Apply learned patterns
6. ✅ Unit tests for NLP components

### What You Need to Do:
- [ ] Nothing! This is all code.

### Deliverables:
- ✅ NLP layer is modular and testable
- ✅ Old `gemini_nlp.py` can be deprecated
- ✅ Pattern matching integrated

### Testing:
- [ ] Run NLP tests: `pytest tests/test_nlp.py`
- [ ] Test intent classification with sample messages
- [ ] Test entity extraction
- [ ] Test pattern matching (even without learning system yet)

---

## Phase 4: Core Message Processing & Handlers

**Goal:** Build the core message processing engine and intent handlers.

### What I'll Build:
1. ✅ `core/processor.py` - Main message processor
2. ✅ `core/context.py` - Conversation context
3. ✅ `core/session.py` - Session management
4. ✅ `handlers/base_handler.py` - Base handler class
5. ✅ `handlers/food_handler.py` - Food logging
6. ✅ `handlers/water_handler.py` - Water logging
7. ✅ `handlers/gym_handler.py` - Gym logging
8. ✅ `handlers/todo_handler.py` - Todo/reminder management
9. ✅ `handlers/query_handler.py` - Data queries
10. ✅ `responses/formatter.py` - Response formatting
11. ✅ Refactored `app.py` (minimal Flask entry point)

### What You Need to Do:

#### 1. Update Twilio Webhook (if deploying)
- [ ] If using production URL, update Twilio webhook to point to your app
- [ ] Test webhook receives messages

#### 2. Test SMS Flow
- [ ] Send test SMS: "ate a quesadilla"
- [ ] Verify response
- [ ] Check database for logged entry

### Deliverables:
- ✅ Core chatbot works with new architecture
- ✅ All basic intents work (food, water, gym, todos)
- ✅ `app.py` is now ~200 lines (down from 3769)
- ✅ Old monolithic code can be removed

### Testing:
- [ ] Send test SMS messages for each intent
- [ ] Verify data is saved correctly
- [ ] Verify responses are formatted well
- [ ] Check logs for errors

---

## Phase 5: Learning System

**Goal:** Implement adaptive learning that learns user patterns.

### What I'll Build:
1. ✅ `learning/pattern_extractor.py` - Extract patterns from messages
2. ✅ `learning/association_learner.py` - Learn associations
3. ✅ `learning/context_analyzer.py` - Detect learning opportunities
4. ✅ `learning/knowledge_base.py` - Knowledge storage/retrieval
5. ✅ `core/learning.py` - Learning orchestrator
6. ✅ Integration with message processor
7. ✅ Unit tests for learning system

### What You Need to Do:
- [ ] Nothing! This is all code.

### Deliverables:
- ✅ System can learn user patterns
- ✅ Learned patterns are applied automatically
- ✅ Patterns stored per user

### Testing:
- [ ] Send: "I had dhamaka practice today, count it as a workout"
- [ ] Verify pattern was learned
- [ ] Send: "had dhamaka practice"
- [ ] Verify system recognizes it as workout automatically
- [ ] Check database for learned pattern

---

## Phase 6: Web Dashboard & Authentication

**Goal:** Build web dashboard for account management and data visualization.

### What I'll Build:
1. ✅ `web/auth.py` - Authentication (login, register, password reset)
2. ✅ `web/routes.py` - Dashboard routes
3. ✅ `web/dashboard.py` - Dashboard data endpoints
4. ✅ `templates/dashboard/index.html` - Main dashboard
5. ✅ `templates/dashboard/login.html` - Login page
6. ✅ `templates/dashboard/register.html` - Registration page
7. ✅ `templates/dashboard/settings.html` - Settings page
8. ✅ Updated CSS for dashboard
9. ✅ User registration flow
10. ✅ Phone verification flow

### What You Need to Do:

#### 1. Email Setup (for password reset)
- [ ] Set up email service (Gmail App Password, SendGrid, etc.)
- [ ] Add to `.env`:
  ```bash
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your_email@gmail.com
  SMTP_PASSWORD=your_app_password
  FROM_EMAIL=your_email@gmail.com
  ```

#### 2. Test Web Dashboard
- [ ] Visit `http://localhost:5000/dashboard`
- [ ] Create test account
- [ ] Verify phone verification SMS
- [ ] Log in and view dashboard
- [ ] Test password reset flow

### Deliverables:
- ✅ Users can register accounts
- ✅ Users can log in
- ✅ Dashboard shows user data
- ✅ Settings page works

### Testing:
- [ ] Create new user account
- [ ] Verify phone number
- [ ] Log in
- [ ] View dashboard with data
- [ ] Test password reset

---

## Phase 7: Third-Party Integrations

**Goal:** Add Fitbit, Google Calendar, and Google Fit integrations.

### What I'll Build:
1. ✅ `integrations/base.py` - Base integration interface
2. ✅ `integrations/auth.py` - OAuth manager
3. ✅ `integrations/sync_manager.py` - Sync orchestration
4. ✅ `integrations/health/fitbit/` - Fitbit integration
5. ✅ `integrations/calendar/google_calendar/` - Google Calendar
6. ✅ `integrations/health/google_fit/` - Google Fit
7. ✅ `data/integration_repository.py` - Integration storage
8. ✅ `web/integrations.py` - Integration management UI
9. ✅ Webhook handlers for real-time updates

### What You Need to Do:

#### 1. Fitbit Developer Setup
- [ ] Go to [dev.fitbit.com](https://dev.fitbit.com)
- [ ] Create app
- [ ] Set OAuth 2.0 redirect URI: `https://your-domain.com/integrations/fitbit/callback`
- [ ] Get Client ID and Client Secret
- [ ] Add to `.env`:
  ```bash
  FITBIT_CLIENT_ID=your_client_id
  FITBIT_CLIENT_SECRET=your_client_secret
  ```

#### 2. Google Cloud Setup
- [ ] Go to [console.cloud.google.com](https://console.cloud.google.com)
- [ ] Create project (or use existing)
- [ ] Enable APIs:
  - Google Calendar API
  - Google Fit API
- [ ] Create OAuth 2.0 credentials
- [ ] Set authorized redirect URIs:
  - `https://your-domain.com/integrations/google/calendar/callback`
  - `https://your-domain.com/integrations/google/fit/callback`
- [ ] Get Client ID and Client Secret
- [ ] Add to `.env`:
  ```bash
  GOOGLE_CLIENT_ID=your_client_id
  GOOGLE_CLIENT_SECRET=your_client_secret
  GOOGLE_REDIRECT_URI=https://your-domain.com/integrations/google/calendar/callback
  ```

#### 3. Webhook URLs (for production)
- [ ] Fitbit: Set webhook URL in Fitbit app settings
- [ ] Google: Set up Pub/Sub or webhook endpoints
- [ ] Update webhook URLs in your deployment

#### 4. Test Integrations
- [ ] Connect Fitbit account via dashboard
- [ ] Verify OAuth flow works
- [ ] Check sync happens
- [ ] Connect Google Calendar
- [ ] Verify calendar events sync

### Deliverables:
- ✅ Users can connect Fitbit
- ✅ Users can connect Google Calendar
- ✅ Users can connect Google Fit
- ✅ Data syncs automatically
- ✅ Webhooks receive updates

### Testing:
- [ ] Connect each integration
- [ ] Verify data syncs
- [ ] Test webhook receives updates
- [ ] Test disconnect flow
- [ ] Test conflict resolution

---

## Phase 8: Background Jobs & Services

**Goal:** Move all scheduled tasks to background services.

### What I'll Build:
1. ✅ `services/scheduler.py` - Background job scheduler
2. ✅ `services/reminder_service.py` - Reminder checking
3. ✅ `services/sync_service.py` - Periodic syncs
4. ✅ `services/notification_service.py` - Notifications
5. ✅ Integration with APScheduler
6. ✅ Health check endpoints

### What You Need to Do:

#### 1. Redis Setup (optional, for caching)
- [ ] Install Redis locally OR
- [ ] Use Redis cloud service (Redis Cloud, Upstash)
- [ ] Add to `.env`:
  ```bash
  REDIS_URL=redis://localhost:6379
  # OR
  REDIS_URL=redis://your-redis-cloud-url
  ```

#### 2. Test Background Jobs
- [ ] Start app
- [ ] Verify scheduler starts
- [ ] Check logs for scheduled jobs
- [ ] Test reminder delivery
- [ ] Test sync jobs

### Deliverables:
- ✅ All background jobs work
- ✅ Reminders are sent
- ✅ Syncs happen automatically
- ✅ Health checks work

### Testing:
- [ ] Verify scheduler starts on app startup
- [ ] Test reminder delivery
- [ ] Test sync jobs run
- [ ] Check health endpoints: `/health`, `/health/ready`, `/health/live`

---

## Post-Implementation: Security & Optimization

**Goal:** Add security hardening and performance optimizations.

### What I'll Build (incrementally):
1. ✅ Input validation & sanitization
2. ✅ Rate limiting
3. ✅ Security headers
4. ✅ Query optimization
5. ✅ Caching layer
6. ✅ Error handling improvements
7. ✅ Logging improvements
8. ✅ Monitoring setup

### What You Need to Do:
- [ ] Review security checklist
- [ ] Set up monitoring (if desired)
- [ ] Configure production environment variables
- [ ] Test rate limiting
- [ ] Review logs

---

## Quick Reference: Environment Variables

### Required for Basic Functionality
```bash
# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
YOUR_PHONE_NUMBER=

# Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Flask
FLASK_SECRET_KEY=
ENCRYPTION_KEY=
```

### Required for Web Dashboard (Phase 6)
```bash
# Email (password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
FROM_EMAIL=
```

### Required for Integrations (Phase 7)
```bash
# Fitbit
FITBIT_CLIENT_ID=
FITBIT_CLIENT_SECRET=

# Google
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
```

### Optional
```bash
# Redis (caching)
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Testing Checklist (After Each Phase)

- [ ] Code runs without errors
- [ ] Database operations work
- [ ] SMS messages are received and processed
- [ ] Responses are sent correctly
- [ ] Data is saved to database
- [ ] No errors in logs
- [ ] Unit tests pass (if applicable)

---

## Rollback Plan

If something goes wrong:

1. **Code Issues:**
   - Revert to backup branch: `git checkout backup-before-rebuild`
   - Or revert specific commits

2. **Database Issues:**
   - Supabase has automatic backups
   - Can restore from backup in Supabase dashboard
   - Or re-run schema creation SQL

3. **Environment Issues:**
   - Keep backup of `.env` file
   - Restore from backup

---

## Support & Questions

If you encounter issues:
1. Check logs for error messages
2. Verify environment variables are set
3. Test database connection
4. Verify API keys are valid
5. Check Supabase dashboard for database issues

---

## Next Steps

1. **Start with Phase 0** - Complete all setup tasks
2. **Then Phase 1** - I'll build foundation, you run SQL
3. **Continue phase by phase** - Each phase is independent
4. **Test after each phase** - Don't move on until current phase works

Ready to start? Let me know when you've completed Phase 0 setup, and I'll begin Phase 1!
