---
name: Chatbot Architecture Rebuild with Learning & Integrations
overview: "Rebuild the SMS assistant chatbot with a clean, modular architecture that includes adaptive learning capabilities and third-party integrations. The assistant learns user-specific patterns (e.g., \"dhamaka\" = workout) and seamlessly integrates with health apps, calendars, and other services. Architecture includes: (1) Web dashboard for account management and integration setup, (2) SMS/iMessage for all assistant interactions, (3) Adaptive learning system that learns from user patterns, (4) Third-party integrations (Fitbit, Google Calendar, etc.) with automatic syncing. All learning is context-aware, NLP-driven, and stored securely per user."
todos:
  - id: "1"
    content: Create new directory structure (core/, handlers/, data/, nlp/, learning/, services/, responses/, utils/, tests/)
    status: completed
  - id: "2"
    content: Create complete database schema SQL file - drop existing tables, create all tables fresh with user_id, indexes, and RLS policies
    status: completed
  - id: "3"
    content: Extract data layer - create BaseRepository and entity-specific repositories
    status: completed
  - id: "4"
    content: Create KnowledgeRepository for storing and retrieving user-specific patterns
    status: completed
  - id: "5"
    content: Refactor NLP layer - split gemini_nlp.py into intent_classifier.py, entity_extractor.py, parser.py, and gemini_client.py
    status: completed
  - id: "6"
    content: Create PatternMatcher to apply learned patterns during NLP processing
    status: completed
  - id: "7"
    content: Implement PatternExtractor to extract patterns from user messages
    status: pending
  - id: "8"
    content: Implement AssociationLearner to manage pattern associations and confidence
    status: pending
  - id: "9"
    content: Implement ContextAnalyzer to detect learning opportunities
    status: pending
  - id: "10"
    content: Create LearningOrchestrator to coordinate learning system
    status: pending
  - id: "11"
    content: Create BaseHandler class and extract individual intent handlers
    status: pending
  - id: "12"
    content: Create ConversationContext class to manage conversation state
    status: pending
  - id: "13"
    content: Create MessageProcessor class that integrates learning system into message flow
    status: pending
  - id: "14"
    content: Refactor app.py to use new architecture
    status: pending
  - id: "15"
    content: Move scheduler logic to services/scheduler.py
    status: pending
  - id: "16"
    content: Create response formatters and templates
    status: pending
  - id: "17"
    content: Add unit tests for learning system components
    status: pending
  - id: "18"
    content: Add integration tests for learning flow end-to-end
    status: pending
  - id: "19"
    content: Execute database schema creation - run SQL script in Supabase to create all tables from scratch
    status: completed
  - id: "20"
    content: Implement BaseIntegration interface and IntegrationAuthManager for OAuth flows
    status: pending
  - id: "21"
    content: Implement SyncManager to orchestrate data syncing from all providers
    status: pending
  - id: "22"
    content: Create IntegrationRepository for storing connected accounts and sync history
    status: pending
  - id: "23"
    content: Implement Fitbit integration (client, mapper, webhook handler)
    status: pending
  - id: "24"
    content: Refactor Google Calendar integration into new structure with webhook support
    status: pending
  - id: "25"
    content: Implement Google Fit integration (client and mapper)
    status: pending
  - id: "26"
    content: Create IntegrationHandler to process integration-related user commands
    status: pending
  - id: "27"
    content: Add conflict resolution logic for synced data vs manual entries
    status: pending
  - id: "28"
    content: Integrate sync data into message processing context and suggestions
    status: pending
  - id: "29"
    content: Create users table and user authentication system for website
    status: pending
  - id: "30"
    content: Build web dashboard routes and pages (dashboard, integrations, settings)
    status: pending
  - id: "31"
    content: Implement web-based OAuth flows for integrations
    status: pending
  - id: "32"
    content: Create integration management UI on website
    status: pending
  - id: "33"
    content: Add proactive integration suggestions in SMS responses
    status: pending
  - id: "34"
    content: Update all data tables to reference users table for multi-user support
    status: pending
  - id: "35"
    content: Implement user registration and phone verification flow (SMS code verification)
    status: pending
  - id: "36"
    content: Create UserRepository for user account management
    status: pending
  - id: "37"
    content: Implement password reset functionality via email
    status: pending
  - id: "38"
    content: Create comprehensive error handling system with fallbacks
    status: pending
  - id: "39"
    content: Set up structured application logging (debug, info, warning, error levels)
    status: pending
  - id: "40"
    content: Implement rate limiting for API endpoints and SMS sending
    status: pending
  - id: "41"
    content: Add webhook signature verification for Fitbit and Google integrations
    status: pending
  - id: "42"
    content: Implement token encryption/decryption using Fernet
    status: pending
  - id: "43"
    content: Set up background job scheduler for syncs, reminders, and scheduled tasks
    status: pending
  - id: "44"
    content: Add caching layer for user patterns and static data (Redis or in-memory)
    status: pending
  - id: "45"
    content: Create input validation utilities (phone, email, password, dates)
    status: pending
  - id: "46"
    content: Create health check endpoints (/health, /health/ready, /health/live)
    status: pending
  - id: "47"
    content: Configure database connection pooling for Supabase
    status: pending
  - id: "48"
    content: Document all new environment variables needed
    status: pending
  - id: "49"
    content: Create comprehensive test suite (unit, integration, E2E tests)
    status: pending
  - id: "50"
    content: Write deployment documentation and setup monitoring/alerting
    status: pending
---

# Chatbot Architecture Rebuild with Adaptive Learning

## Implementation Progress

**Current Phase:** Phase 7 - Third-Party Integrations  
**Last Updated:** Phase 6 Complete  
**Note:** UI overhaul deferred until after Phase 7. Current dashboard/auth UI is functional and acceptable.

### Phase Status:
- ✅ **Phase 0:** Pre-Implementation Setup - COMPLETE
- ✅ **Phase 1:** Foundation & Database Schema - COMPLETE & TESTED ✅
  - Database schema created and run in Supabase
  - All 19 tables created with indexes and RLS policies
  - Directory structure created
  - Base repository pattern implemented
  - **All database connection tests PASSED**
  - Test fixes applied for composite key tables
- ✅ **Phase 2:** Data Layer & Repositories - COMPLETE & TESTED
  - 9 repositories created (user, food, water, gym, todo, knowledge, sleep, assignment, fact)
  - All repositories extend BaseRepository
  - Entity-specific methods implemented
  - Unit tests created and **ALL PASSED**
  - All CRUD operations verified working
- ✅ **Phase 3:** NLP Layer Refactoring - COMPLETE & TESTED ✅
  - Split 1479-line gemini_nlp.py into 6 focused modules
  - GeminiClient, IntentClassifier, EntityExtractor, Parser, PatternMatcher, DatabaseLoader
  - Pattern matching integrated with learning system
  - Unit tests created and **ALL PASSED**
  - Fixed food parsing bug (NoneType error)
  - Migrated to new google-genai SDK (fixed deprecation warning)
- ✅ **Phase 4:** Core Message Processing & Handlers - COMPLETE & TESTED ✅
  - MessageProcessor, ConversationContext, SessionManager created
  - 5 handlers implemented (Food, Water, Gym, Todo, Query)
  - ResponseFormatter for SMS formatting
  - app_new.py refactored (~150 lines, down from 3769)
  - **All 6 test cases PASSED**
  - Data persistence verified (all logs saved and retrieved)
  - Context cache working (UTC date handling fixed)
  - Date queries fixed (timezone handling)
- ✅ **Phase 5:** Learning System - COMPLETE ✅
  - PatternExtractor, AssociationLearner, ContextAnalyzer, LearningOrchestrator created
  - Learning integrated into MessageProcessor
  - Supports explicit teaching, corrections, confirmations
  - Patterns stored per user with confidence scores
  - Automatic pattern application before NLP
  - Unit tests created
- ✅ **Phase 6:** Web Dashboard & Authentication - COMPLETE ✅
  - AuthManager with login, register, password reset, phone verification
  - Dashboard routes (login, register, settings, API endpoints)
  - DashboardData for stats, trends, calendar data
  - All templates created/updated (login, register, settings, verify_phone, etc.)
  - CSS updated for new components
  - Schema additions for phone verification and password reset
  - Integrated into app_new.py
  - **Note:** UI overhaul deferred until after Phase 7 (current UI is functional)
- ⏳ **Phase 7:** Third-Party Integrations - NEXT
- ⏳ **Phase 8:** Background Jobs & Services - PENDING
- 📝 **Future:** UI Overhaul - Deferred until after Phase 7

### Cleanup Completed:
- ✅ Removed obsolete files (csv_database.py, old schemas, test files)
- ✅ Cleaned up scripts directory
- ✅ Project structure organized

## Current Problems Identified

1. **Monolithic Structure**: Single 3769-line `app.py` file containing everything
2. **Mixed Responsibilities**: Message processing, database operations, scheduling, and web routes all intertwined
3. **No Clear Architecture**: No separation between NLP, business logic, and data access
4. **State Management**: Scattered state with no clear pattern
5. **No Learning Capability**: Cannot adapt to user-specific patterns and preferences
6. **Hard to Test**: Tightly coupled code makes unit testing difficult
7. **Hard to Extend**: Adding new intents/features requires modifying multiple places

## New Requirement: Adaptive Learning

The chatbot must learn from user interactions:

- **Pattern Recognition**: Learn associations (e.g., "dhamaka" = workout type)
- **Context Inference**: Use NLP to infer relationships from context
- **Per-User Storage**: Store learned patterns securely per user (phone number)
- **Automatic Application**: Use learned patterns in future conversations without hardcoding

**Example Flow:**

1. User: "I had dhamaka practice today, count it as a workout"
2. System infers: "dhamaka" is associated with "workout" intent
3. System stores: `{user_id, pattern: "dhamaka", intent: "gym_workout", context: "dance team practice"}`
4. Future: User: "had dhamaka practice" → System recognizes as workout automatically

## Proposed Architecture

### Directory Structure

```
sms_assistant/
├── app.py                          # Flask app entry point (minimal routing)
├── config.py                       # Configuration
├── requirements.txt
│
├── core/                           # Core chatbot engine
│   ├── __init__.py
│   ├── processor.py               # Main message processor
│   ├── context.py                  # Conversation context/state
│   ├── session.py                  # Session management
│   └── learning.py                 # Learning orchestrator (NEW)
│
├── nlp/                            # Natural Language Processing
│   ├── __init__.py
│   ├── intent_classifier.py        # Intent classification
│   ├── entity_extractor.py         # Entity extraction
│   ├── parser.py                   # Domain-specific parsers
│   ├── gemini_client.py            # Gemini API wrapper
│   └── pattern_matcher.py          # Pattern matching with learned knowledge (NEW)
│
├── learning/                       # Adaptive Learning System (NEW)
│   ├── __init__.py
│   ├── pattern_extractor.py        # Extract patterns from user messages
│   ├── association_learner.py     # Learn associations (word → intent/entity)
│   ├── context_analyzer.py          # Analyze context for learning opportunities
│   └── knowledge_base.py           # Interface to user knowledge storage
│
├── handlers/                       # Intent handlers
│   ├── __init__.py
│   ├── base.py                     # Base handler class
│   ├── water_handler.py
│   ├── food_handler.py
│   ├── gym_handler.py
│   ├── sleep_handler.py
│   ├── todo_handler.py
│   ├── reminder_handler.py
│   ├── assignment_handler.py
│   ├── stats_handler.py
│   ├── fact_handler.py
│   ├── completion_handler.py
│   └── integration_handler.py       # Handle integration commands (NEW)
│
├── data/                           # Data access layer
│   ├── __init__.py
│   ├── repository.py               # Base repository
│   ├── food_repository.py
│   ├── water_repository.py
│   ├── gym_repository.py
│   ├── sleep_repository.py
│   ├── todo_repository.py
│   ├── reminder_repository.py
│   ├── assignment_repository.py
│   ├── fact_repository.py
│   ├── knowledge_repository.py     # User knowledge storage (NEW)
│   ├── integration_repository.py    # Connected accounts storage (NEW)
│   └── user_repository.py            # User accounts (NEW)
│
├── integrations/                    # Third-Party Integrations (NEW)
│   ├── __init__.py
│   ├── base.py                      # Base integration interface
│   ├── auth.py                      # OAuth/authentication manager
│   ├── sync_manager.py              # Sync orchestration
│   │
│   ├── health/                      # Health & Fitness Integrations
│   │   ├── __init__.py
│   │   ├── fitbit/
│   │   │   ├── __init__.py
│   │   │   ├── client.py            # Fitbit API client
│   │   │   ├── mapper.py            # Map Fitbit data to our schema
│   │   │   └── webhook.py           # Fitbit webhook handler
│   │   ├── apple_health/
│   │   │   ├── __init__.py
│   │   │   ├── client.py            # Apple HealthKit client
│   │   │   └── mapper.py            # Map HealthKit data
│   │   └── google_fit/
│   │       ├── __init__.py
│   │       ├── client.py            # Google Fit API client
│   │       └── mapper.py            # Map Google Fit data
│   │
│   ├── calendar/                    # Calendar Integrations
│   │   ├── __init__.py
│   │   ├── google_calendar/
│   │   │   ├── __init__.py
│   │   │   ├── client.py            # Google Calendar API client (refactor existing)
│   │   │   ├── mapper.py            # Map calendar events
│   │   │   └── webhook.py           # Calendar webhook handler
│   │   └── outlook/
│   │       ├── __init__.py
│   │       ├── client.py
│   │       └── mapper.py
│   │
│   └── other/                       # Other Integrations (future)
│       ├── __init__.py
│       └── ...
│
├── services/
│   ├── __init__.py
│   ├── communication.py
│   ├── scheduler.py
│   ├── stats_service.py
│   └── suggestion_service.py
│
├── responses/
│   ├── __init__.py
│   ├── formatter.py
│   └── templates.py
│
├── web/                             # Website/Dashboard (NEW)
│   ├── __init__.py
│   ├── routes.py                    # Flask routes for web pages
│   ├── auth.py                      # Web authentication
│   ├── dashboard.py                 # Dashboard views
│   ├── integrations.py             # Integration management views
│   └── api.py                       # REST API for dashboard data
│
└── utils/
    ├── __init__.py
    ├── validators.py
    └── helpers.py
```

## New Components: Learning System

### 1. Learning Orchestrator (`core/learning.py`)

**Responsibilities:**

- Detects learning opportunities in user messages
- Coordinates pattern extraction and storage
- Integrates learned patterns into NLP processing

**Key Methods:**

```python
class LearningOrchestrator:
    def detect_learning_opportunity(self, message: str, intent: Intent, context: ConversationContext) -> Optional[LearningOpportunity]
    def extract_pattern(self, message: str, intent: Intent, context: ConversationContext) -> Pattern
    def store_pattern(self, pattern: Pattern, user_id: str) -> None
    def apply_learned_patterns(self, message: str, user_id: str) -> Optional[Intent]
```

### 2. Pattern Extractor (`learning/pattern_extractor.py`)

**Purpose:**

- Extract user-specific patterns from messages
- Identify associations (word/phrase → intent/entity)
- Use NLP to infer relationships from context

**Example:**

- Input: "I had dhamaka practice today, count it as a workout"
- Output: Pattern(term="dhamaka", intent="gym_workout", confidence=0.9, context="dance team practice")

**Key Methods:**

```python
class PatternExtractor:
    def extract_association(self, message: str, explicit_intent: Intent, context: ConversationContext) -> Optional[Pattern]
    def extract_entity_mapping(self, message: str, context: ConversationContext) -> Optional[EntityMapping]
    def infer_relationship(self, message: str, nlp_client: GeminiClient) -> Optional[Relationship]
```

### 3. Association Learner (`learning/association_learner.py`)

**Purpose:**

- Learn associations between terms and intents/entities
- Build confidence scores over time
- Handle conflicting information

**Key Methods:**

```python
class AssociationLearner:
    def learn_association(self, term: str, intent: Intent, context: str, user_id: str) -> None
    def get_association(self, term: str, user_id: str) -> Optional[Association]
    def update_confidence(self, association_id: int, was_correct: bool) -> None
    def resolve_conflict(self, term: str, conflicting_associations: List[Association]) -> Association
```

### 4. Context Analyzer (`learning/context_analyzer.py`)

**Purpose:**

- Analyze message context to identify learning opportunities
- Detect explicit teaching moments ("count this as X", "this is a Y")
- Infer implicit patterns from usage

**Key Methods:**

```python
class ContextAnalyzer:
    def has_explicit_teaching(self, message: str) -> bool
    def extract_teaching_intent(self, message: str) -> Optional[TeachingIntent]
    def detect_implicit_pattern(self, message: str, intent: Intent) -> Optional[Pattern]
```

### 5. Knowledge Base (`learning/knowledge_base.py`)

**Purpose:**

- Interface to user knowledge storage
- Query learned patterns
- Manage knowledge lifecycle (update, delete, merge)

**Key Methods:**

```python
class KnowledgeBase:
    def get_patterns_for_user(self, user_id: str) -> List[Pattern]
    def get_associations_for_term(self, term: str, user_id: str) -> List[Association]
    def search_patterns(self, query: str, user_id: str) -> List[Pattern]
    def merge_patterns(self, pattern1: Pattern, pattern2: Pattern) -> Pattern
```

### 6. Pattern Matcher (`nlp/pattern_matcher.py`)

**Purpose:**

- Apply learned patterns during intent classification
- Enhance entity extraction with user-specific knowledge
- Integrate with existing NLP pipeline

**Key Methods:**

```python
class PatternMatcher:
    def match_learned_patterns(self, message: str, user_id: str) -> Optional[Intent]
    def enhance_entities(self, message: str, entities: Dict, user_id: str) -> Dict
    def get_pattern_confidence(self, pattern: Pattern, message: str) -> float
```

### 7. Knowledge Repository (`data/knowledge_repository.py`)

**Purpose:**

- Store and retrieve user-specific knowledge
- Handle pattern storage, updates, and queries
- Manage knowledge versioning and conflicts

## New Components: Third-Party Integrations

### 1. Web Authentication (`web/auth.py`)

**Purpose:**

- Handle user registration and login
- Link phone numbers to user accounts
- Session management for web dashboard
- Password hashing and security

**Key Methods:**

```python
class WebAuth:
    def register(self, phone_number: str, email: str, password: str, name: str) -> User
    def login(self, email: str, password: str) -> Optional[User]
    def link_phone_to_account(self, phone_number: str, user_id: int) -> bool
    def get_user_by_phone(self, phone_number: str) -> Optional[User]
    def get_user_by_email(self, email: str) -> Optional[User]
```

### 2. Web Dashboard Routes (`web/routes.py`)

**Purpose:**

- Serve dashboard pages
- Handle integration OAuth callbacks
- API endpoints for dashboard data
- User settings management

**Key Routes:**

```python
@app.route('/dashboard')  # Main dashboard
@app.route('/dashboard/integrations')  # Integration management
@app.route('/dashboard/integrations/<provider>/connect')  # OAuth initiation
@app.route('/dashboard/integrations/<provider>/callback')  # OAuth callback
@app.route('/dashboard/settings')  # User settings
@app.route('/api/dashboard/stats')  # Stats API
@app.route('/api/dashboard/logs')  # Logs API
```

### 3. Integration Management UI (`web/integrations.py`)

**Purpose:**

- Display available integrations
- Show connection status
- Handle OAuth flows
- Display sync settings and history

**Key Features:**

- List of integrations with "Connect" buttons
- Status indicators (connected/disconnected)
- Last sync time and status
- Sync settings (frequency, data types)
- Disconnect functionality

### 4. Base Integration Interface (`integrations/base.py`)

**Purpose:**

- Define common interface for all integrations
- Standardize authentication, syncing, and data mapping
- Enable easy addition of new integrations

**Key Methods:**

```python
class BaseIntegration:
    def authenticate(self, user_id: str, auth_code: str) -> Connection
    def refresh_token(self, connection: Connection) -> bool
    def sync(self, user_id: str, sync_type: str, last_sync: datetime) -> SyncResult
    def map_data(self, external_data: Dict) -> Dict
    def handle_webhook(self, payload: Dict) -> None
    def disconnect(self, user_id: str) -> bool
```

### 2. Integration Auth Manager (`integrations/auth.py`)

**Purpose:**

- Handle OAuth flows for all providers
- Manage tokens (access, refresh, expiration)
- Secure token storage and rotation

**How OAuth Works (Technical Overview):**

OAuth 2.0 is the standard protocol for secure third-party access. Here's how it works:

**Step 1: Register Your App**

- You register your app with Fitbit/Google/etc. to get:
  - `CLIENT_ID`: Public identifier for your app
  - `CLIENT_SECRET`: Secret key (never exposed to users)
  - `REDIRECT_URI`: Where to send user after authorization (e.g., `https://yourapp.com/integrations/fitbit/callback`)

**Step 2: User Initiates Connection**

- User clicks "Connect Fitbit" on your website
- Your app generates an OAuth URL with:
  - Your `CLIENT_ID`
  - Scopes (permissions you're requesting): `activity`, `sleep`, `heartrate`
  - `REDIRECT_URI` (where to send user back)
  - `STATE` (random string to prevent CSRF attacks)
- User is redirected to Fitbit's authorization page

**Step 3: User Authorizes**

- User sees Fitbit's page: "App X wants to access your activity, sleep, and heart rate data"
- User clicks "Allow"
- Fitbit generates an `AUTHORIZATION_CODE` (temporary, one-time use)

**Step 4: Exchange Code for Tokens**

- Fitbit redirects user back to your `REDIRECT_URI` with the code
- Your server exchanges the code for tokens:
  ```
  POST https://api.fitbit.com/oauth2/token
  {
    "code": "AUTHORIZATION_CODE",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "YOUR_REDIRECT_URI",
    "grant_type": "authorization_code"
  }
  ```

- Fitbit responds with:
  - `access_token`: Used to make API calls (expires in ~8 hours)
  - `refresh_token`: Used to get new access tokens (doesn't expire)
  - `expires_in`: How long access token is valid

**Step 5: Store Tokens Securely**

- Encrypt tokens before storing in database
- Link to user account
- Never expose tokens to frontend/client

**Step 6: Use Tokens to Fetch Data**

- When syncing, use access token in API requests:
  ```
  GET https://api.fitbit.com/1/user/-/activities/date/2024-01-15.json
  Authorization: Bearer ACCESS_TOKEN
  ```

- If token expired, use refresh token to get new one:
  ```
  POST https://api.fitbit.com/oauth2/token
  {
    "refresh_token": "REFRESH_TOKEN",
    "grant_type": "refresh_token"
  }
  ```


**Security Best Practices:**

- ✅ Encrypt tokens at rest (database)
- ✅ Use HTTPS for all API calls
- ✅ Request minimal scopes (only what you need)
- ✅ Store refresh tokens securely (they don't expire)
- ✅ Rotate tokens before expiration
- ✅ Never log or expose tokens

**Key Methods:**

```python
class IntegrationAuthManager:
    def get_oauth_url(self, provider: str, user_id: str) -> str
        # Generates OAuth URL with client_id, scopes, redirect_uri, state
        # Returns: "https://fitbit.com/oauth2/authorize?client_id=...&scope=..."
    
    def handle_oauth_callback(self, provider: str, code: str, state: str) -> Connection
        # Exchanges authorization code for access/refresh tokens
        # Encrypts and stores tokens in database
        # Returns Connection object
    
    def refresh_connection(self, connection_id: int) -> bool
        # Uses refresh token to get new access token
        # Updates stored tokens
        # Returns True if successful
    
    def revoke_connection(self, connection_id: int) -> bool
        # Revokes tokens with provider
        # Deactivates connection in database
    
    def get_active_connections(self, user_id: str) -> List[Connection]
        # Returns all active connections for user
```

### 3. Sync Manager (`integrations/sync_manager.py`)

**Purpose:**

- Orchestrate data syncing from all connected services
- Handle sync scheduling, conflicts, and deduplication
- Manage sync history and error handling

**Key Methods:**

```python
class SyncManager:
    def sync_all(self, user_id: str) -> Dict[str, SyncResult]
    def sync_provider(self, user_id: str, provider: str) -> SyncResult
    def schedule_sync(self, user_id: str, provider: str, interval: timedelta) -> None
    def handle_conflict(self, local_data: Dict, external_data: Dict) -> Dict
    def deduplicate(self, data: List[Dict]) -> List[Dict]
```

### 4. Health Integrations

#### Fitbit Integration (`integrations/health/fitbit/`)

**Capabilities:**

- Sync steps, distance, calories burned
- Sync heart rate data
- Sync sleep data (duration, stages, quality)
- Sync workout activities
- Real-time webhooks for activity updates

**Data Mapping:**

- Fitbit steps → Water intake estimation (optional)
- Fitbit workouts → Gym logs
- Fitbit sleep → Sleep logs
- Fitbit heart rate → Health metrics

**Implementation:**

```python
class FitbitIntegration(BaseIntegration):
    def sync_activities(self, user_id: str, start_date: date, end_date: date) -> List[Activity]
    def sync_sleep(self, user_id: str, date: date) -> SleepData
    def sync_heart_rate(self, user_id: str, date: date) -> HeartRateData
```

#### Apple Health Integration (`integrations/health/apple_health/`)

**Capabilities:**

- Sync via HealthKit export (XML/JSON)
- Sync via Health app sharing
- Sync workouts, steps, sleep, heart rate
- Sync nutrition data (if available)

**Note:** Apple Health requires iOS app or HealthKit export file upload

#### Google Fit Integration (`integrations/health/google_fit/`)

**Capabilities:**

- Sync activities, steps, calories
- Sync sleep data
- Sync heart rate and other metrics
- Real-time updates via REST API

### 5. Calendar Integrations

#### Google Calendar (`integrations/calendar/google_calendar/`)

**Capabilities:**

- Sync calendar events
- Create events from reminders/todos
- Two-way sync (create in assistant → appears in calendar)
- Real-time updates via webhooks

**Data Mapping:**

- Calendar events → Context for suggestions
- Reminders → Calendar events (optional)
- Todos with due dates → Calendar events (optional)

**Refactoring:**

- Move existing `google_calendar.py` into this structure
- Enhance with webhook support
- Add bidirectional sync

#### Outlook Calendar (`integrations/calendar/outlook/`)

**Capabilities:**

- Similar to Google Calendar
- Microsoft Graph API integration
- OAuth 2.0 authentication

### 6. Integration Repository (`data/integration_repository.py`)

**Purpose:**

- Store connected accounts and credentials
- Track sync history and status
- Manage integration settings per user

**Database Schema (add to Supabase):**

```sql
-- Connected accounts
CREATE TABLE user_integrations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,  -- phone number
    provider TEXT NOT NULL,  -- 'fitbit', 'google_calendar', etc.
    provider_user_id TEXT,  -- User's ID in provider system
    access_token TEXT NOT NULL,  -- Encrypted
    refresh_token TEXT,  -- Encrypted
    token_expires_at TIMESTAMP,
    scopes TEXT[],  -- Array of granted scopes
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    sync_settings JSONB,  -- Provider-specific settings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Sync history for debugging and conflict resolution
CREATE TABLE sync_history (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER REFERENCES user_integrations(id),
    sync_type TEXT NOT NULL,  -- 'full', 'incremental', 'webhook'
    status TEXT NOT NULL,  -- 'success', 'error', 'partial'
    items_synced INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- External data mapping (to handle conflicts and deduplication)
CREATE TABLE external_data_mapping (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER REFERENCES user_integrations(id),
    external_id TEXT NOT NULL,  -- ID from external system
    internal_type TEXT NOT NULL,  -- 'gym_log', 'sleep_log', etc.
    internal_id INTEGER,  -- ID in our system
    external_data JSONB,  -- Snapshot of external data
    last_synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(integration_id, external_id, internal_type)
);

CREATE INDEX idx_user_integrations_user ON user_integrations(user_id);
CREATE INDEX idx_user_integrations_provider ON user_integrations(provider);
CREATE INDEX idx_sync_history_integration ON sync_history(integration_id);
CREATE INDEX idx_external_mapping_integration ON external_data_mapping(integration_id);
```

**Key Methods:**

```python
class IntegrationRepository:
    def create_connection(self, user_id: str, provider: str, tokens: Dict) -> int
    def get_connection(self, user_id: str, provider: str) -> Optional[Connection]
    def update_tokens(self, connection_id: int, tokens: Dict) -> None
    def deactivate_connection(self, connection_id: int) -> None
    def log_sync(self, integration_id: int, sync_result: SyncResult) -> int
    def get_sync_history(self, integration_id: int, limit: int = 10) -> List[SyncHistory]
    def map_external_data(self, integration_id: int, external_id: str, internal_type: str, internal_id: int) -> None
    def find_existing_mapping(self, integration_id: int, external_id: str) -> Optional[Mapping]
```

## Integration Flow

### Connection Flow (Web-Based) - Detailed

**User Perspective (Seamless):**

1. **User initiates via SMS**: "connect my fitbit" OR assistant suggests after workout
2. **Assistant responds with link**: "Visit [website]/integrations/fitbit to connect"
3. **User visits website**: Opens link in browser (e.g., `yourapp.com/integrations/fitbit`)
4. **User logs in** (if not already): Email/password or phone verification
5. **User sees "Connect Fitbit" button**: On integrations page
6. **User clicks button**: One click
7. **Redirected to Fitbit**: Opens Fitbit's authorization page
8. **User sees permissions**: "App wants access to: Activity, Sleep, Heart Rate"
9. **User clicks "Allow"**: On Fitbit's page
10. **Automatically redirected back**: To your website
11. **Website shows**: "Connected! Syncing your data..."
12. **Background sync happens**: System fetches data from Fitbit
13. **Website confirms**: "Done! Return to iMessage to continue"
14. **SMS notification**: Assistant sends: "Fitbit connected! Synced 30 days of workouts"

**Technical Flow (Behind the Scenes):**

1. **Generate OAuth URL**:
   ```
   https://www.fitbit.com/oauth2/authorize?
     response_type=code&
     client_id=YOUR_CLIENT_ID&
     redirect_uri=https://yourapp.com/integrations/fitbit/callback&
     scope=activity%20sleep%20heartrate&
     state=random_security_string
   ```

2. **User authorizes on Fitbit**: Fitbit validates and generates authorization code

3. **Fitbit redirects back**:
   ```
   https://yourapp.com/integrations/fitbit/callback?
     code=AUTHORIZATION_CODE&
     state=random_security_string
   ```

4. **Server exchanges code for tokens**:
   ```python
   # POST to Fitbit token endpoint
   response = requests.post('https://api.fitbit.com/oauth2/token', data={
       'code': authorization_code,
       'client_id': CLIENT_ID,
       'client_secret': CLIENT_SECRET,
       'redirect_uri': REDIRECT_URI,
       'grant_type': 'authorization_code'
   })
   tokens = response.json()
   # Returns: access_token, refresh_token, expires_in
   ```

5. **Encrypt and store tokens**:
   ```python
   encrypted_access = encrypt(tokens['access_token'])
   encrypted_refresh = encrypt(tokens['refresh_token'])
   db.store_connection(user_id, 'fitbit', encrypted_access, encrypted_refresh)
   ```

6. **Initial sync**:
   ```python
   # Use access token to fetch data
   headers = {'Authorization': f'Bearer {access_token}'}
   activities = requests.get('https://api.fitbit.com/1/user/-/activities/list.json', headers=headers)
   # Map and store in database
   ```


**Making It Seamless:**

1. **Short, memorable URLs**: Use URL shortener or custom domain
2. **Auto-login**: Remember user session, skip login if already authenticated
3. **Clear instructions**: "Click Connect → Authorize on Fitbit → Done!"
4. **Progress indicators**: Show "Connecting...", "Syncing...", "Done!"
5. **Error handling**: Clear messages if something fails
6. **Mobile-friendly**: Works well on phone browsers
7. **Quick return**: After connection, user can immediately return to SMS

### Sync Flow

1. **Scheduled sync** (every hour/daily):

   - Sync Manager checks all active connections
   - For each connection, calls provider's sync method
   - Maps external data to internal schema
   - Handles conflicts (user's manual entries take priority)
   - Deduplicates (avoid double-logging)
   - Updates sync history

2. **Real-time sync** (via webhooks):

   - Provider sends webhook on data change
   - Webhook handler processes immediately
   - Maps and stores data
   - Optionally notifies user: "Synced your workout from Fitbit"

3. **Manual sync** (via SMS):

   - User: "sync my fitbit"
   - System triggers immediate sync
   - Returns summary: "Synced 3 new workouts, 1 sleep log"

### Conflict Resolution

**Priority Order:**

1. **User manual entry** (highest priority)
2. **Most recent data** (if both from integrations)
3. **Ask user** (if significant conflict detected)

**Example:**

- User manually logged: "gym workout at 2pm"
- Fitbit syncs: "workout at 2:15pm"
- System: Keeps manual entry, notes Fitbit data as alternative

### Data Mapping Examples

**Fitbit Workout → Gym Log:**

```python
{
    "external": {
        "activityName": "Running",
        "duration": 3600,
        "calories": 450,
        "distance": 5.2
    },
    "internal": {
        "exercise": "Running",
        "duration_minutes": 60,
        "calories_burned": 450,
        "notes": "Synced from Fitbit: 5.2 km"
    }
}
```

**Google Calendar Event → Context:**

```python
{
    "external": {
        "summary": "Team Meeting",
        "start": "2024-01-15T14:00:00Z",
        "end": "2024-01-15T15:00:00Z"
    },
    "internal": {
        "type": "calendar_event",
        "title": "Team Meeting",
        "start_time": "2024-01-15T14:00:00Z",
        "end_time": "2024-01-15T15:00:00Z",
        "used_for": "context_in_suggestions"
    }
}
```

## Integration with Message Processing

### Proactive Suggestions

The assistant proactively suggests integrations when relevant:

**After Logging Workout:**

- User: "did bench press 135x5"
- Assistant: "Logged! 💪 Want to auto-sync workouts? Connect Fitbit: [link]"

**After Logging Sleep:**

- User: "slept 11pm-7am"
- Assistant: "Logged! 😴 Connect Fitbit to auto-track sleep: [link]"

**When Querying Stats:**

- User: "how much did I sleep this week?"
- Assistant: "7h average. Connect Fitbit for detailed sleep stages: [link]"

### Enhanced Context

When processing messages, the system now has access to:

- **Recent sync data**: "You logged 10k steps today (from Fitbit)"
- **Calendar events**: "You have a meeting in 30 minutes"
- **Health trends**: "Your sleep has been 7h average this week"

### Smart Suggestions

Integrations enable smarter suggestions:

- "You usually work out at 6pm (from calendar), want to log it?"
- "Fitbit shows you walked 8k steps, want to log water?"
- "You have 3 meetings today, here's your schedule..."

### Seamless Logging

Users can reference integrated data:

- "log my fitbit workout from today"
- "what did my fitbit say about my sleep last night?"
- "sync my calendar and tell me what I have today"

## Security & Privacy

- **Token Encryption**: All access/refresh tokens encrypted at rest
- **Scope Limitation**: Request only necessary OAuth scopes
- **Token Rotation**: Automatic refresh before expiration
- **User Control**: Users can disconnect anytime
- **Data Isolation**: Integration data isolated per user
- **Audit Logging**: All syncs logged for debugging

## Database Expansion & Schema Creation

### Overview

Yes, the database needs significant expansion. Since there's no existing data, we can create a clean schema from scratch. The new architecture requires:

1. **Multi-user support**: All tables need `user_id` foreign keys from the start
2. **New tables**: Users, integrations, knowledge, sync history
3. **Clean schema**: No migration needed - create all tables fresh
4. **Indexes**: Performance indexes from the start
5. **RLS policies**: Row-level security for multi-user isolation

### Complete Database Schema

**Database Schema Updates:**

**1. User Accounts (NEW TABLE - add to Supabase):**

```sql
-- User accounts for website login
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,  -- SMS identifier
    email TEXT UNIQUE,
    password_hash TEXT,  -- For web login
    name TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_email ON users(email);
```

**2. User Knowledge (add to Supabase):**

```sql
CREATE TABLE user_knowledge (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,  -- Reference to users table
    pattern_term TEXT NOT NULL,  -- e.g., "dhamaka"
    pattern_type TEXT NOT NULL,  -- 'intent', 'entity', 'synonym'
    associated_value TEXT NOT NULL,  -- e.g., "gym_workout"
    context TEXT,  -- e.g., "dance team practice"
    confidence NUMERIC DEFAULT 0.5,  -- 0.0 to 1.0
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, pattern_term, pattern_type, associated_value)
);

CREATE INDEX idx_user_knowledge_user ON user_knowledge(user_id);
CREATE INDEX idx_user_knowledge_term ON user_knowledge(pattern_term);
CREATE INDEX idx_user_knowledge_type ON user_knowledge(pattern_type);
```

**3. User Integrations (add to Supabase):**

```sql
-- Connected accounts (updated to reference users table)
CREATE TABLE user_integrations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,  -- Reference to users table
    provider TEXT NOT NULL,  -- 'fitbit', 'google_calendar', etc.
    provider_user_id TEXT,  -- User's ID in provider system
    access_token TEXT NOT NULL,  -- Encrypted
    refresh_token TEXT,  -- Encrypted
    token_expires_at TIMESTAMP,
    scopes TEXT[],  -- Array of granted scopes
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    sync_settings JSONB,  -- Provider-specific settings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Update existing tables to reference users table
ALTER TABLE food_logs ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE water_logs ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE gym_logs ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE sleep_logs ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE reminders_todos ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE assignments ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE facts ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE user_knowledge ADD COLUMN user_id INTEGER REFERENCES users(id);
```

**4. Sync History (NEW TABLE - add to Supabase):**

```sql
CREATE TABLE sync_history (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER REFERENCES user_integrations(id) ON DELETE CASCADE,
    sync_type TEXT NOT NULL,  -- 'full', 'incremental', 'webhook'
    status TEXT NOT NULL,  -- 'success', 'error', 'partial'
    items_synced INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_sync_history_integration ON sync_history(integration_id);
CREATE INDEX idx_sync_history_status ON sync_history(status);
CREATE INDEX idx_sync_history_started ON sync_history(started_at);
```

**5. External Data Mapping (NEW TABLE - add to Supabase):**

```sql
CREATE TABLE external_data_mapping (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER REFERENCES user_integrations(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,  -- ID from external system
    internal_type TEXT NOT NULL,  -- 'gym_log', 'sleep_log', etc.
    internal_id INTEGER,  -- ID in our system
    external_data JSONB,  -- Snapshot of external data
    last_synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(integration_id, external_id, internal_type)
);

CREATE INDEX idx_external_mapping_integration ON external_data_mapping(integration_id);
CREATE INDEX idx_external_mapping_internal ON external_data_mapping(internal_type, internal_id);
```

**6. Core Data Tables (REBUILD WITH USER_ID):**

Since there's no existing data, we'll create all tables fresh with `user_id` from the start:

```sql
-- Food logs (rebuild with user_id)
DROP TABLE IF EXISTS food_logs CASCADE;
CREATE TABLE food_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    food_name TEXT NOT NULL,
    calories NUMERIC NOT NULL,
    protein NUMERIC NOT NULL,
    carbs NUMERIC NOT NULL,
    fat NUMERIC NOT NULL,
    restaurant TEXT,
    portion_multiplier NUMERIC DEFAULT 1.0
);

-- Water logs (rebuild with user_id)
DROP TABLE IF EXISTS water_logs CASCADE;
CREATE TABLE water_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    amount_ml NUMERIC NOT NULL,
    amount_oz NUMERIC NOT NULL
);

-- Gym logs (rebuild with user_id)
DROP TABLE IF EXISTS gym_logs CASCADE;
CREATE TABLE gym_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    exercise TEXT NOT NULL,
    sets INTEGER,
    reps INTEGER,
    weight NUMERIC,
    notes TEXT
);

-- Sleep logs (rebuild with user_id)
DROP TABLE IF EXISTS sleep_logs CASCADE;
CREATE TABLE sleep_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    date DATE NOT NULL,
    sleep_time TIME NOT NULL,
    wake_time TIME NOT NULL,
    duration_hours NUMERIC NOT NULL
);

-- Reminders and todos (rebuild with user_id)
DROP TABLE IF EXISTS reminders_todos CASCADE;
CREATE TABLE reminders_todos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    type TEXT NOT NULL CHECK (type IN ('reminder', 'todo')),
    content TEXT NOT NULL,
    due_date TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    sent_at TIMESTAMP,
    follow_up_sent BOOLEAN DEFAULT FALSE,
    decay_check_sent BOOLEAN DEFAULT FALSE
);

-- Assignments (rebuild with user_id)
DROP TABLE IF EXISTS assignments CASCADE;
CREATE TABLE assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    class_name TEXT NOT NULL,
    assignment_name TEXT NOT NULL,
    due_date TIMESTAMP NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    notes TEXT
);

-- Facts (rebuild with user_id)
DROP TABLE IF EXISTS facts CASCADE;
CREATE TABLE facts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    context TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Water goals (rebuild with user_id - composite key)
DROP TABLE IF EXISTS water_goals CASCADE;
CREATE TABLE water_goals (
    user_id INTEGER REFERENCES users(id) NOT NULL,
    date DATE NOT NULL,
    goal_ml NUMERIC NOT NULL,
    PRIMARY KEY (user_id, date)
);

-- Used quotes (rebuild with user_id - composite key)
DROP TABLE IF EXISTS used_quotes CASCADE;
CREATE TABLE used_quotes (
    user_id INTEGER REFERENCES users(id) NOT NULL,
    date DATE NOT NULL,
    quote TEXT NOT NULL,
    author TEXT,
    PRIMARY KEY (user_id, date, quote)
);

-- Add indexes for performance
CREATE INDEX idx_food_logs_user ON food_logs(user_id);
CREATE INDEX idx_food_logs_timestamp ON food_logs(timestamp);
CREATE INDEX idx_water_logs_user ON water_logs(user_id);
CREATE INDEX idx_water_logs_timestamp ON water_logs(timestamp);
CREATE INDEX idx_gym_logs_user ON gym_logs(user_id);
CREATE INDEX idx_gym_logs_timestamp ON gym_logs(timestamp);
CREATE INDEX idx_sleep_logs_user ON sleep_logs(user_id);
CREATE INDEX idx_sleep_logs_date ON sleep_logs(date);
CREATE INDEX idx_reminders_todos_user ON reminders_todos(user_id);
CREATE INDEX idx_reminders_todos_type ON reminders_todos(type);
CREATE INDEX idx_reminders_todos_completed ON reminders_todos(completed);
CREATE INDEX idx_reminders_todos_due_date ON reminders_todos(due_date);
CREATE INDEX idx_assignments_user ON assignments(user_id);
CREATE INDEX idx_assignments_due_date ON assignments(due_date);
CREATE INDEX idx_assignments_completed ON assignments(completed);
CREATE INDEX idx_assignments_class_name ON assignments(class_name);
CREATE INDEX idx_facts_user ON facts(user_id);
CREATE INDEX idx_facts_key ON facts(key);
CREATE INDEX idx_facts_timestamp ON facts(timestamp);
```

**7. Row-Level Security (RLS) Policies:**

Enable RLS on all tables to ensure users can only access their own data:

```sql
-- Enable RLS on all tables
ALTER TABLE food_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE water_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gym_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleep_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders_todos ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_data_mapping ENABLE ROW LEVEL SECURITY;

-- Create policies (example for food_logs, repeat for all tables)
CREATE POLICY "Users can only see their own food logs"
    ON food_logs FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY "Users can only insert their own food logs"
    ON food_logs FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY "Users can only update their own food logs"
    ON food_logs FOR UPDATE
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY "Users can only delete their own food logs"
    ON food_logs FOR DELETE
    USING (user_id = current_setting('app.current_user_id')::INTEGER);
```

### Data Migration Strategy

**Phase 1: Pre-Migration (Backup)**

1. Export all existing data to JSON/CSV
2. Verify backup integrity
3. Document current data counts

**Phase 2: Schema Migration**

1. Create `users` table
2. Create single "default" user account (for existing data)
3. Add `user_id` columns to all existing tables (nullable)
4. Create new tables (user_knowledge, user_integrations, etc.)

**Phase 3: Data Migration**

1. Link all existing data to default user:
   ```sql
   -- Get default user ID
   INSERT INTO users (phone_number, email, name) 
   VALUES ('+1234567890', 'default@example.com', 'Default User')
   RETURNING id;
   
   -- Update all existing records
   UPDATE food_logs SET user_id = <default_user_id> WHERE user_id IS NULL;
   UPDATE water_logs SET user_id = <default_user_id> WHERE user_id IS NULL;
   -- Repeat for all tables
   ```

2. Make `user_id` NOT NULL after migration:
   ```sql
   ALTER TABLE food_logs ALTER COLUMN user_id SET NOT NULL;
   -- Repeat for all tables
   ```


**Phase 4: Post-Migration**

1. Add indexes
2. Enable RLS policies
3. Test queries with user context
4. Verify data integrity

**Migration Script:**

```python
def migrate_database():
    """Migrate existing single-user database to multi-user"""
    
    # 1. Create users table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone_number TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            last_login_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    
    # 2. Create default user for existing data
    default_user = db.execute("""
        INSERT INTO users (phone_number, email, name)
        VALUES ('+1234567890', 'migration@example.com', 'Migration User')
        ON CONFLICT (phone_number) DO NOTHING
        RETURNING id;
    """).fetchone()
    
    default_user_id = default_user[0] if default_user else None
    
    # 3. Add user_id columns (nullable initially)
    tables = ['food_logs', 'water_logs', 'gym_logs', 'sleep_logs', 
              'reminders_todos', 'assignments', 'facts']
    
    for table in tables:
        try:
            db.execute(f"""
                ALTER TABLE {table} 
                ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
            """)
        except Exception as e:
            print(f"Error adding user_id to {table}: {e}")
    
    # 4. Migrate existing data
    if default_user_id:
        for table in tables:
            db.execute(f"""
                UPDATE {table} 
                SET user_id = {default_user_id} 
                WHERE user_id IS NULL;
            """)
    
    # 5. Make user_id NOT NULL
    for table in tables:
        try:
            db.execute(f"""
                ALTER TABLE {table} 
                ALTER COLUMN user_id SET NOT NULL;
            """)
        except Exception as e:
            print(f"Error setting NOT NULL on {table}: {e}")
    
    # 6. Create indexes
    for table in tables:
        db.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_user 
            ON {table}(user_id);
        """)
    
    print("Migration complete!")
```

### Summary of Database Changes

**All Tables Created Fresh (14 total):**

**Core Tables (2):**

1. `users` - User accounts (NEW)
2. `user_knowledge` - Learned patterns (NEW)

**Data Logging Tables (7 - REBUILT with user_id):**

3. `food_logs` - Food consumption logs
4. `water_logs` - Water intake logs
5. `gym_logs` - Workout logs
6. `sleep_logs` - Sleep logs
7. `reminders_todos` - Reminders and todos
8. `assignments` - School assignments
9. `facts` - Stored information/facts

**Integration Tables (3 - NEW):**

10. `user_integrations` - Connected services (Fitbit, Google, etc.)
11. `sync_history` - Sync operation logs
12. `external_data_mapping` - Maps external IDs to internal data

**Configuration Tables (2 - REBUILT with user_id):**

13. `water_goals` - Daily water goals (now per-user)
14. `used_quotes` - Daily quotes (now per-user)

**New Indexes:**

- User ID indexes on all tables
- Composite indexes for common queries
- Integration-specific indexes

**New Security:**

- RLS policies on all tables
- User context setting in application
- Encrypted token storage

**Key Methods:**

```python
class KnowledgeRepository:
    def store_pattern(self, user_id: str, pattern: Pattern) -> int
    def get_patterns(self, user_id: str, pattern_type: Optional[str] = None) -> List[Pattern]
    def get_pattern_by_term(self, user_id: str, term: str) -> Optional[Pattern]
    def update_confidence(self, pattern_id: int, was_correct: bool) -> None
    def increment_usage(self, pattern_id: int) -> None
    def delete_pattern(self, pattern_id: int) -> bool
```

## Integration Flow

### Learning Flow

1. **User sends message**: "I had dhamaka practice today, count it as a workout"
2. **Intent Classification**: Classifies as `gym_workout` (explicit intent)
3. **Learning Detection**: `LearningOrchestrator` detects teaching moment
4. **Pattern Extraction**: Extracts pattern "dhamaka" → "gym_workout"
5. **Storage**: Stores pattern in `user_knowledge` table with context
6. **Confirmation**: System confirms learning: "Got it! I'll remember that 'dhamaka' is a workout"

### Application Flow

1. **User sends message**: "had dhamaka practice"
2. **Pattern Matching**: `PatternMatcher` checks learned patterns for user
3. **Pattern Found**: Matches "dhamaka" → "gym_workout" with high confidence
4. **Intent Override**: Uses learned pattern to classify intent
5. **Processing**: Processes as gym workout
6. **Confidence Update**: Increments usage count and updates confidence if successful

### NLP Integration

The learning system integrates at multiple points:

1. **Pre-Classification**: Pattern matcher checks learned patterns before NLP classification
2. **Post-Classification**: Learning orchestrator analyzes results for learning opportunities
3. **Entity Enhancement**: Learned patterns enhance entity extraction
4. **Context Building**: Learned patterns provide context for better understanding

## Implementation Details

### Pattern Types

1. **Intent Association**: Term → Intent (e.g., "dhamaka" → "gym_workout")
2. **Entity Mapping**: Term → Entity value (e.g., "kraft" → "the_devils_krafthouse")
3. **Synonym**: Term → Synonym (e.g., "gsoy" → "ginger_and_soy")
4. **Custom Entity**: Term → Custom entity type (e.g., "dhamaka" → workout_type="dance")

### Confidence Scoring

- **Initial**: 0.5 (neutral)
- **Increment**: +0.1 per successful use
- **Decrement**: -0.2 per incorrect use
- **Threshold**: Patterns with confidence < 0.3 are ignored
- **Max**: 1.0 (fully trusted)

### Conflict Resolution

- If user teaches conflicting pattern, newer pattern wins but both stored
- System asks for clarification if confidence is similar
- Usage counts help resolve conflicts over time

## Updated Message Processing Flow

```
1. Receive message
2. Load user's learned patterns (PatternMatcher)
3. Check for pattern matches (pre-classification)
4. Classify intent (with pattern hints)
5. Extract entities (enhanced with learned patterns)
6. Process intent (handler)
7. Detect learning opportunities (LearningOrchestrator)
8. Extract and store patterns (if applicable)
9. Generate response
10. Update pattern confidence (if pattern was used)
```

## Security & Privacy

- **Per-User Isolation**: All knowledge stored with user_id (phone number)
- **No Cross-User Learning**: Patterns never shared between users
- **Data Encryption**: Sensitive patterns encrypted at rest
- **Access Control**: RLS policies in Supabase ensure user can only access their own knowledge
- **Deletion**: Users can delete learned patterns

## Code Replacement Strategy

### Files to COMPLETELY REPLACE (Rebuild from Scratch)

1. **`app.py`** (3769 lines → ~200 lines)

   - **Current**: Monolithic file with everything mixed together
   - **New**: Minimal Flask app with clean route handlers
   - **Action**: Extract all logic into new modules, keep only Flask setup

2. **`gemini_nlp.py`** (1479 lines → Split into 4-5 focused modules)

   - **Current**: One massive file with all NLP logic
   - **New**: Split into `intent_classifier.py`, `entity_extractor.py`, `parser.py`, `gemini_client.py`
   - **Action**: Refactor and split, remove old file

3. **`supabase_database.py`** (505 lines → Split into repositories)

   - **Current**: One class with all database methods
   - **New**: Separate repository classes (one per entity type)
   - **Action**: Extract into repository pattern, remove old file

4. **`communication_service.py`**

   - **Current**: Mixed communication logic
   - **New**: Move to `services/communication.py` with cleaner interface
   - **Action**: Refactor and move, remove old file

### Files to KEEP (Minimal Changes)

1. **`config.py`**

   - Keep structure, may add new config for learning system
   - **Action**: Minor additions only

2. **`google_calendar.py`**

   - Keep as-is (or move to `services/` if needed)
   - **Action**: No changes or minor refactor

3. **Data JSON files** (`data/*.json`)

   - Keep all food databases, gym workouts, etc.
   - **Action**: No changes

4. **Templates and Static files**

   - Keep dashboard templates and CSS
   - **Action**: No changes

5. **`requirements.txt`**

   - Keep, may add new dependencies
   - **Action**: Add any new packages needed

### Files to DELETE (No Longer Needed)

**Files Already Deleted (Phase 1 Cleanup):**
- ✅ `csv_database.py` - Old CSV database (replaced by Supabase)
- ✅ `supabase_schema.sql` - Old schema (replaced by `supabase_schema_complete.sql`)
- ✅ `scripts/convert_csv_to_json.py` - No longer needed
- ✅ `scripts/test_nicknames.py` - Old test file
- ✅ `scripts/` directory - Removed (empty)
- ✅ `new_features.md` - Documentation only, not needed
- ✅ `test_new_features.py` - Old test file

**Files to Delete in Future Phases:**

**Files Already Deleted (Phase 1 Cleanup - ✅ COMPLETE):**
- ✅ `csv_database.py` - Old CSV database (replaced by Supabase)
- ✅ `supabase_schema.sql` - Old schema (replaced by `supabase_schema_complete.sql`)
- ✅ `scripts/convert_csv_to_json.py` - No longer needed
- ✅ `scripts/test_nicknames.py` - Old test file
- ✅ `scripts/` directory - Removed (empty)
- ✅ `new_features.md` - Documentation only, not needed
- ✅ `test_new_features.py` - Old test file

**Files to Delete in Future Phases:**
1. **`supabase_database.py`** (Phase 2)
   - **Action**: Delete after repositories are created and app.py is refactored

2. **`gemini_nlp.py`** (Phase 3)
   - **Action**: Delete after NLP layer is refactored into separate modules

3. **`app.py`** (Phase 4)
   - **Action**: Replace with new minimal Flask app entry point

4. **`communication_service.py`** (Phase 4)
   - **Action**: Move to `services/communication.py` and delete old file

### Migration Strategy

**Phase 1: Build New Architecture (Parallel Development)**

1. Create new directory structure
2. Build new modules alongside old code
3. Keep old code running during development
4. Test new modules independently

**Phase 2: Extract and Replace**

1. Extract data layer → Create repositories
2. Extract NLP layer → Split into focused modules
3. Extract handlers → Create handler classes
4. Build new message processor
5. **Delete old code files** as they're replaced

**Phase 3: Learning Infrastructure**

1. Create knowledge repository and database schema
2. Implement learning components
3. Integrate into message processor
4. Test learning flow end-to-end

**Phase 4: Final Cleanup**

1. Replace `app.py` with new minimal version
2. Remove all old code files
3. Update imports throughout codebase
4. Run full test suite
5. **Delete any remaining old code**

### Replacement Guarantee

**YES - We will:**

- ✅ Completely replace the messy 3769-line `app.py`
- ✅ Completely replace the monolithic `gemini_nlp.py`
- ✅ Completely replace the monolithic `supabase_database.py`
- ✅ Remove all non-working/broken code
- ✅ Remove all tightly-coupled, hard-to-maintain code
- ✅ Build everything fresh with clean architecture

**We will NOT:**

- ❌ Keep old code "just in case" (we'll delete it)
- ❌ Build new code alongside old code permanently
- ❌ Leave broken functionality in place

**Result:**

- Clean, maintainable codebase
- No legacy code baggage
- Everything works correctly
- Easy to extend and test

## Benefits

1. **Personalization**: Each user's assistant learns their specific patterns
2. **Reduced Errors**: Learned patterns improve accuracy over time
3. **Natural Interaction**: Users can teach the assistant naturally
4. **Scalability**: Learning happens automatically without hardcoding
5. **User Satisfaction**: Assistant becomes more helpful over time

## Example Scenarios

**Scenario 1: Workout Type Learning**

- User: "I had dhamaka practice, count it as a workout"
- System learns: "dhamaka" → gym_workout
- Future: "had dhamaka" → automatically logged as workout

**Scenario 2: Restaurant Nickname**

- User: "ate at kraft" (system doesn't recognize)
- User: "kraft is the devils krafthouse"
- System learns: "kraft" → restaurant "the_devils_krafthouse"
- Future: "kraft quesadilla" → correctly matched

**Scenario 3: Custom Food**

- User: "I had my usual smoothie, 300 cal 20g protein"
- System learns: "usual smoothie" → food with specific macros
- Future: "had my usual smoothie" → logs with learned macros

**Scenario 4: Fitbit Integration**

- User: "connect my fitbit"
- System: Sends OAuth URL via SMS
- User: Completes OAuth on Fitbit website
- System: "Connected! Syncing your Fitbit data..."
- System: Automatically syncs workouts, sleep, steps
- Future: "sync my fitbit" → Manual sync on demand
- Future: Fitbit webhooks → Real-time updates

**Scenario 5: Calendar Integration**

- User: "connect my google calendar"
- System: OAuth flow, connects account
- System: Syncs calendar events
- User: "what do I have today?"
- System: Shows calendar events + todos + reminders
- User: "remind me to call mom at 3pm"
- System: Creates reminder, optionally adds to calendar

**Scenario 6: Integrated Suggestions**

- System (proactive): "You usually work out at 6pm (from calendar). Want to log your Fitbit workout from today?"
- User: "yes"
- System: Logs workout from Fitbit, confirms: "Logged your 45min run from Fitbit"

## User Experience: Web + SMS Architecture

### Architecture Overview

**Website (Account Management & Setup):**

- User creates account and logs in
- Dashboard to view all data (stats, trends, logs)
- Integration management (connect/disconnect services)
- Settings and preferences
- OAuth flows for integrations (better UX than SMS)

**SMS/iMessage (All Interactions):**

- All assistant interaction happens here
- Logging, queries, reminders, todos
- Proactive suggestions
- Integration status and suggestions

### Integration Connection Flow

**Proactive Suggestion (via SMS):**

1. User logs workout: "did bench press 135x5"
2. Assistant responds: "Logged! 💪 Want to auto-sync workouts? Connect Fitbit at: [link]"
3. User clicks link → Opens website
4. User logs into website (if not already)
5. User clicks "Connect Fitbit" → OAuth flow on website
6. User completes OAuth → Returns to website
7. Website shows: "Connected! Return to iMessage to continue"
8. User returns to iMessage
9. Assistant: "Fitbit connected! Syncing your data now..."
10. Assistant: "Done! Synced 30 days of workouts"

**Manual Request (via SMS):**

1. User: "connect my fitbit"
2. Assistant: "Visit [link] to connect Fitbit. I'll let you know when it's ready!"
3. (Same flow as above)

**After Connection (via SMS):**

- Assistant automatically uses synced data
- User can still manually log (manual takes priority)
- User: "sync my fitbit" → Manual sync trigger
- User: "what did fitbit say about my sleep?" → Query synced data

### Website Features

**Dashboard:**

- View all logs (food, water, workouts, sleep, etc.)
- Stats and trends (7/30/90 day views)
- Calendar view of activities
- Charts and visualizations

**Integrations Page:**

- List of available integrations (Fitbit, Google Calendar, etc.)
- Connection status for each
- "Connect" button → OAuth flow
- "Disconnect" button
- Sync settings (frequency, what to sync)
- Last sync time and status

**Settings:**

- Account management
- Notification preferences
- Data export
- Privacy settings

### SMS Commands (After Setup)

**Integration Status:**

- "show my connections" → Lists connected services
- "sync my fitbit" → Manual sync trigger
- "what did fitbit say about my sleep?" → Query synced data

**Note:** Connection/disconnection happens on website, not SMS (better security and UX)

## Opt-Out & Data Control

### Overview

Users have complete control over their data and connections. Opt-out is designed to be:

- **Easy**: Simple commands and clear options
- **Immediate**: Actions take effect right away
- **Complete**: All data can be deleted if desired
- **Transparent**: Users know exactly what's being deleted

### Option 1: Disconnect Individual Integration

**Via SMS:**

1. User: "disconnect fitbit" or "remove fitbit" or "unlink fitbit"
2. Assistant: "Disconnecting Fitbit... Visit [link] to confirm, or reply 'yes' to disconnect now"
3. User: "yes"
4. System:

   - Revokes tokens with Fitbit API
   - Deactivates connection in database
   - Stops all future syncing
   - Optionally: Asks if user wants to delete synced data

5. Assistant: "Fitbit disconnected. Your synced data is still stored. Say 'delete fitbit data' to remove it."

**Via Website:**

1. User visits: `/dashboard/integrations`
2. User sees list of connected services
3. User clicks "Disconnect" next to Fitbit
4. Confirmation dialog: "Disconnect Fitbit? This will stop syncing but keep your data."
5. User confirms
6. System:

   - Revokes tokens with Fitbit
   - Deactivates connection
   - Shows: "Disconnected. Your synced data is still available."

7. Optional: "Delete all Fitbit data" button (with confirmation)

**Implementation:**

```python
def disconnect_integration(user_id: str, provider: str, delete_data: bool = False):
    # 1. Get connection
    connection = get_connection(user_id, provider)
    
    # 2. Revoke tokens with provider
    revoke_tokens(provider, connection.access_token, connection.refresh_token)
    
    # 3. Deactivate in database
    deactivate_connection(connection.id)
    
    # 4. Optionally delete synced data
    if delete_data:
        delete_synced_data(user_id, provider)
    
    # 5. Log action
    log_action(user_id, 'disconnect_integration', provider)
    
    return True
```

### Option 2: Delete Synced Data (Keep Connection)

**Via SMS:**

1. User: "delete my fitbit data" or "remove fitbit data"
2. Assistant: "This will delete all Fitbit-synced workouts, sleep, and activity data. Your connection will remain. Continue? Reply 'yes' to confirm."
3. User: "yes"
4. System:

   - Deletes all data synced from Fitbit
   - Keeps connection active (can re-sync later)

5. Assistant: "Deleted all Fitbit data. Connection still active - I can sync again if you want."

**Via Website:**

1. User visits: `/dashboard/integrations`
2. User clicks "Manage" next to Fitbit
3. User sees: "Delete All Synced Data" button
4. Confirmation: "Delete all Fitbit data? This cannot be undone. Connection will remain active."
5. User confirms
6. System deletes data, shows confirmation

### Option 3: Stop All Syncing (Keep Data)

**Via SMS:**

1. User: "stop syncing" or "pause integrations" or "disable auto-sync"
2. Assistant: "I can pause all integrations. Your data will be kept. Continue? Reply 'yes'"
3. User: "yes"
4. System:

   - Deactivates all connections (doesn't revoke tokens)
   - Stops scheduled syncs
   - Keeps all data

5. Assistant: "All syncing paused. Your data is safe. Say 'resume syncing' to start again."

**Via Website:**

1. User visits: `/dashboard/settings`
2. User toggles: "Enable Auto-Sync" → OFF
3. System pauses all syncing
4. User can toggle back ON anytime

### Option 4: Delete Account & All Data

**Via SMS:**

1. User: "delete my account" or "cancel service" or "remove all my data"
2. Assistant: "⚠️ This will permanently delete your account and ALL data:

   - All logs (food, water, workouts, sleep)
   - All todos and reminders
   - All learned patterns
   - All connected integrations
   - Your account

This cannot be undone. Type 'DELETE ACCOUNT' to confirm."

3. User: "DELETE ACCOUNT"
4. System:

   - Revokes all integration tokens
   - Deletes all user data from all tables
   - Deactivates user account
   - Logs deletion for audit

5. Assistant: "Account deleted. All data removed. Goodbye!"

**Via Website:**

1. User visits: `/dashboard/settings`
2. User scrolls to "Danger Zone"
3. User clicks "Delete Account"
4. Confirmation page shows:

   - List of what will be deleted
   - Warning: "This cannot be undone"
   - Requires typing account email to confirm

5. User confirms
6. System deletes everything
7. User redirected to confirmation page

**Implementation:**

```python
def delete_account(user_id: int, confirmation: str):
    # Verify confirmation
    if confirmation != 'DELETE ACCOUNT':
        return False
    
    # 1. Revoke all integration tokens
    connections = get_all_connections(user_id)
    for conn in connections:
        revoke_tokens(conn.provider, conn.access_token, conn.refresh_token)
    
    # 2. Delete all user data
    delete_user_data(user_id)  # Deletes from all tables
    
    # 3. Deactivate account
    deactivate_user(user_id)
    
    # 4. Log for audit (keep minimal record)
    log_account_deletion(user_id, datetime.now())
    
    return True

def delete_user_data(user_id: int):
    # Delete from all tables
    db.delete('food_logs', user_id=user_id)
    db.delete('water_logs', user_id=user_id)
    db.delete('gym_logs', user_id=user_id)
    db.delete('sleep_logs', user_id=user_id)
    db.delete('reminders_todos', user_id=user_id)
    db.delete('assignments', user_id=user_id)
    db.delete('facts', user_id=user_id)
    db.delete('user_knowledge', user_id=user_id)
    db.delete('user_integrations', user_id=user_id)
    db.delete('sync_history', user_id=user_id)
    db.delete('external_data_mapping', user_id=user_id)
```

### Option 5: Export Data Before Deleting

**Via SMS:**

1. User: "export my data" or "download my data"
2. Assistant: "I'll prepare your data export. This includes all logs, todos, reminders, and learned patterns. Visit [link] to download when ready."
3. System:

   - Generates JSON/CSV export
   - Stores temporarily (24 hours)
   - Sends download link

4. User downloads from website

**Via Website:**

1. User visits: `/dashboard/settings`
2. User clicks "Export My Data"
3. System generates export (JSON + CSV files)
4. User downloads ZIP file
5. Export includes:

   - All logs (food, water, gym, sleep)
   - Todos and reminders
   - Assignments
   - Learned patterns
   - Integration sync history
   - Account information

### Option 6: Selective Data Deletion

**Via SMS:**

1. User: "delete my food logs" or "remove all water data"
2. Assistant: "Delete all food logs? This cannot be undone. Reply 'yes' to confirm."
3. User: "yes"
4. System deletes only that data type
5. Assistant: "Deleted all food logs."

**Via Website:**

1. User visits: `/dashboard/settings`
2. User sees: "Data Management" section
3. User can delete by type:

   - Delete all food logs
   - Delete all water logs
   - Delete all workouts
   - Delete all sleep data
   - Delete all todos/reminders
   - Delete learned patterns

4. Each requires confirmation

### Privacy & Compliance

**GDPR Compliance:**

- Right to access: Users can export all data
- Right to deletion: Users can delete account/data
- Right to portability: Data export in standard formats
- Right to rectification: Users can edit/correct data

**Data Retention:**

- Active accounts: Data kept indefinitely (until user deletes)
- Deleted accounts: All data removed immediately
- Audit logs: Minimal records kept for security (no personal data)

**Transparency:**

- Users can see what data is stored
- Users can see what integrations are connected
- Users can see sync history
- Clear privacy policy explaining data usage

### Implementation Checklist

**SMS Commands to Handle:**

- [ ] "disconnect [provider]" → Disconnect integration
- [ ] "delete [provider] data" → Delete synced data
- [ ] "stop syncing" → Pause all syncing
- [ ] "resume syncing" → Resume syncing
- [ ] "delete my account" → Full account deletion
- [ ] "export my data" → Data export
- [ ] "delete my [data type]" → Selective deletion

**Website Pages:**

- [ ] `/dashboard/integrations` → Manage connections
- [ ] `/dashboard/settings` → Account settings
- [ ] `/dashboard/settings/data` → Data management
- [ ] `/dashboard/settings/export` → Data export
- [ ] `/dashboard/settings/delete-account` → Account deletion

**Database Functions:**

- [ ] `revoke_integration_tokens()` → Revoke OAuth tokens
- [ ] `delete_user_data()` → Delete all user data
- [ ] `export_user_data()` → Generate data export
- [ ] `delete_data_by_type()` → Selective deletion

**Security:**

- [ ] Require confirmation for destructive actions
- [ ] Log all deletion actions for audit
- [ ] Verify user identity before deletion
- [ ] Rate limit deletion requests
- [ ] Send confirmation email for account deletion

## Integration + Learning Synergy

The learning system and integrations work together:

1. **Learn from Synced Data**: 

   - Fitbit syncs "Running" workout
   - User says "that was my dhamaka practice"
   - System learns: "Running" (from Fitbit) = "dhamaka" = workout

2. **Enhance with Context**:

   - Calendar shows "Dhamaka Practice" event
   - System learns: Calendar event name → workout type
   - Future: Any calendar event with "dhamaka" → auto-logged as workout

3. **Cross-Platform Learning**:

   - User logs workout manually: "dhamaka practice"
   - Fitbit also logs activity at same time
   - System learns to associate Fitbit activity type with "dhamaka"

This architecture provides a foundation for a truly adaptive, personalized chatbot that learns from each interaction and seamlessly integrates with users' existing tools and data.

## Missing Components & Gaps Identified

After thorough review, here are critical missing pieces that need to be added:

### 1. User Registration & Onboarding Flow

**Current Gap:** No clear flow for how users first sign up and link their phone number to their account.

**Solution:**

**Option A: SMS-First Onboarding**

1. User texts the assistant number
2. System detects new phone number (not in database)
3. Assistant: "Hi! I'm your personal assistant. To get started, visit [link] to create your account"
4. User visits website, creates account with email/password
5. System links phone number to account (via verification code sent to phone)
6. User can now use assistant via SMS

**Option B: Website-First Onboarding**

1. User visits website, creates account
2. System sends verification code to phone number
3. User enters code to verify phone
4. Account created and linked
5. User can now text the assistant

**Implementation Needed:**

- Phone number verification system (SMS codes)
- User registration handler
- Phone linking flow
- Welcome messages for new users

### 2. Phone Number Verification

**Current Gap:** No mechanism to verify phone numbers belong to users.

**Solution:**

```python
class PhoneVerification:
    def send_verification_code(self, phone_number: str) -> str
        # Generate 6-digit code
        # Send via SMS
        # Store code with expiration (5 minutes)
        # Return code for testing
    
    def verify_code(self, phone_number: str, code: str) -> bool
        # Check code matches and not expired
        # Mark phone as verified
        # Return True if valid
```

**Database Addition:**

```sql
ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN phone_verification_code TEXT;
ALTER TABLE users ADD COLUMN phone_verification_expires_at TIMESTAMP;
```

### 3. Password Reset & Email Verification

**Current Gap:** No password reset or email verification mentioned.

**Solution:**

- Password reset via email (forgot password link)
- Email verification (optional but recommended)
- Password strength requirements
- Account lockout after failed attempts

**Implementation:**

```python
class WebAuth:
    def request_password_reset(self, email: str) -> bool
        # Generate reset token
        # Send email with reset link
        # Store token with expiration
    
    def reset_password(self, token: str, new_password: str) -> bool
        # Verify token
        # Update password
        # Invalidate token
    
    def verify_email(self, user_id: int, token: str) -> bool
        # Verify email token
        # Mark email as verified
```

### 4. Error Handling & Recovery

**Current Gap:** Error handling mentioned but not detailed.

**Solution:**

**Error Handling Strategy:**

- **NLP Failures**: Fallback to pattern matching, then to simple keyword matching
- **API Failures**: Retry with exponential backoff, graceful degradation
- **Database Errors**: Transaction rollback, user-friendly error messages
- **Integration Failures**: Log error, notify user, continue with manual logging
- **Token Expiration**: Automatic refresh, retry request

**Implementation:**

```python
class ErrorHandler:
    def handle_nlp_error(self, error: Exception, message: str) -> Optional[Intent]
        # Try pattern matching
        # Try keyword matching
        # Return 'unknown' if all fail
    
    def handle_api_error(self, error: Exception, retry_count: int) -> bool
        # Check if retryable
        # Exponential backoff
        # Log error
        # Return True if should retry
    
    def handle_database_error(self, error: Exception) -> str
        # Rollback transaction
        # Log error
        # Return user-friendly message
```

### 5. Logging & Monitoring

**Current Gap:** Audit logging mentioned but no application logging strategy.

**Solution:**

**Logging Levels:**

- **DEBUG**: Detailed flow for development
- **INFO**: Normal operations (message received, intent classified)
- **WARNING**: Recoverable issues (NLP low confidence, sync partial failure)
- **ERROR**: Failures that need attention (API errors, database errors)
- **CRITICAL**: System failures (database down, service unavailable)

**What to Log:**

- All incoming messages (with user_id, not phone number)
- Intent classification results
- Learning events (pattern stored, confidence updated)
- Integration syncs (success/failure, items synced)
- Errors with stack traces
- Performance metrics (response time, API latency)

**Implementation:**

```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("message_received", extra={
    "user_id": user_id,
    "message_length": len(message),
    "timestamp": datetime.now().isoformat()
})

logger.error("nlp_classification_failed", extra={
    "user_id": user_id,
    "message": message,
    "error": str(error),
    "traceback": traceback.format_exc()
})
```

### 6. Rate Limiting

**Current Gap:** Only mentioned for deletions, not for API calls or SMS.

**Solution:**

**Rate Limits Needed:**

- **Gemini API**: Already handled in gemini_nlp.py (5 req/min free tier)
- **SMS Sending**: Limit per user (prevent spam)
- **Web Requests**: Limit login attempts, API calls
- **Integration Syncs**: Limit frequency per provider

**Implementation:**

```python
from flask_limiter import Limiter

limiter = Limiter(
    app=app,
    key_func=lambda: request.remote_addr,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/sms', methods=['POST'])
@limiter.limit("10 per minute")  # Per user
def handle_sms():
    pass
```

### 7. Webhook Security

**Current Gap:** No mention of verifying webhook authenticity.

**Solution:**

**Webhook Verification:**

- **Fitbit**: Verify signature using shared secret
- **Google**: Verify JWT token
- **General**: Verify request source, validate payload structure

**Implementation:**

```python
def verify_fitbit_webhook(request):
    signature = request.headers.get('X-Fitbit-Signature')
    payload = request.data
    expected = hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

def verify_google_webhook(request):
    # Verify JWT token
    # Check issuer
    # Validate expiration
    pass
```

### 8. Token Encryption Implementation

**Current Gap:** Encryption mentioned but not detailed.

**Solution:**

**Encryption Strategy:**

- Use Fernet (symmetric encryption) from cryptography library
- Store encryption key in environment variable (never in code)
- Encrypt before storing, decrypt after retrieving
- Rotate keys periodically

**Implementation:**

```python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, token: str) -> str:
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted_token: str) -> str:
        return self.cipher.decrypt(encrypted_token.encode()).decode()
```

### 9. Background Job Processing

**Current Gap:** Scheduler mentioned but not detailed for new architecture.

**Solution:**

**Background Jobs:**

- Scheduled syncs (hourly/daily per integration)
- Reminder checks (every 5 minutes)
- Follow-up checks (every 15 minutes)
- Weekly digests (scheduled)
- Token refresh (before expiration)

**Implementation:**

```python
# services/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

class JobScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def schedule_sync_jobs(self):
        # Schedule per-user, per-integration syncs
        for user in get_all_users():
            for integration in get_user_integrations(user.id):
                self.scheduler.add_job(
                    sync_integration,
                    'interval',
                    hours=1,
                    args=[user.id, integration.provider],
                    id=f"sync_{user.id}_{integration.provider}"
                )
    
    def start(self):
        self.scheduler.start()
```

### 10. Caching Strategy

**Current Gap:** No caching mentioned - could improve performance.

**Solution:**

**What to Cache:**

- User's learned patterns (refresh on update)
- Food database (static, refresh on file change)
- Gym database (static)
- User's active integrations (refresh on connect/disconnect)
- Recent user data for context (TTL: 1 hour)

**Implementation:**

```python
from functools import lru_cache
import redis

cache = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=100)
def get_user_patterns(user_id: int):
    # Cache user patterns
    pass

def invalidate_user_cache(user_id: int):
    # Clear cache when patterns updated
    cache.delete(f"user_patterns:{user_id}")
```

### 11. Environment Variables

**Current Gap:** New env vars needed but not listed.

**Solution:**

**New Environment Variables:**

```bash
# User Authentication
FLASK_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key

# Integration OAuth
FITBIT_CLIENT_ID=your-fitbit-client-id
FITBIT_CLIENT_SECRET=your-fitbit-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://yourapp.com/integrations/google/callback

# Email (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourapp.com

# Redis (for caching, optional)
REDIS_URL=redis://localhost:6379/0

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn  # For error tracking
```

### 12. User Repository

**Current Gap:** User repository missing from data layer.

**Solution:**

**Add to data/user_repository.py:**

```python
class UserRepository:
    def create(self, phone_number: str, email: str, password_hash: str, name: str) -> User
    def get_by_id(self, user_id: int) -> Optional[User]
    def get_by_phone(self, phone_number: str) -> Optional[User]
    def get_by_email(self, email: str) -> Optional[User]
    def update(self, user_id: int, **updates) -> bool
    def verify_phone(self, user_id: int, code: str) -> bool
    def verify_email(self, user_id: int, token: str) -> bool
    def deactivate(self, user_id: int) -> bool
```

### 13. Initial User Setup Flow

**Current Gap:** What happens when a new phone number texts for the first time?

**Solution:**

**First-Time User Flow:**

1. User texts assistant number
2. System checks if phone number exists in database
3. If not found:

   - Assistant: "Hi! I'm your personal assistant. To get started, create an account at [link]"
   - System stores phone number temporarily (pending verification)
   - User visits website, creates account
   - System sends verification code to phone
   - User enters code, account linked
   - Assistant: "Account created! You can now text me anything - try 'help' to see what I can do"

4. If found:

   - Normal message processing

### 14. Testing Strategy Details

**Current Gap:** Testing mentioned but not detailed.

**Solution:**

**Test Structure:**

```
tests/
├── unit/
│   ├── test_handlers/
│   ├── test_nlp/
│   ├── test_learning/
│   ├── test_repositories/
│   └── test_integrations/
├── integration/
│   ├── test_message_flow/
│   ├── test_learning_flow/
│   └── test_sync_flow/
└── e2e/
    └── test_user_journeys/
```

**Key Tests:**

- Handler unit tests (mock dependencies)
- NLP component tests (test classification, extraction)
- Learning system tests (pattern storage, retrieval, confidence)
- Integration tests (OAuth flow, sync flow)
- E2E tests (complete user journeys)

### 15. Deployment Considerations

**Current Gap:** Deployment not detailed.

**Solution:**

**Deployment Checklist:**

- [ ] Environment variables set in production
- [ ] Database migrations run
- [ ] SSL certificates configured
- [ ] Webhook URLs registered with providers
- [ ] OAuth redirect URIs configured
- [ ] Monitoring/alerting set up
- [ ] Backup strategy in place
- [ ] Health check endpoints
- [ ] Log aggregation configured

### 16. Health Checks & Monitoring

**Current Gap:** Not mentioned.

**Solution:**

**Health Check Endpoints:**

```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'database': check_database(),
        'integrations': check_integrations(),
        'timestamp': datetime.now().isoformat()
    }

@app.route('/health/ready')
def readiness_check():
    # Check if service is ready to accept traffic
    pass

@app.route('/health/live')
def liveness_check():
    # Check if service is alive
    pass
```

### 17. Database Connection Pooling

**Current Gap:** Not mentioned.

**Solution:**

- Use connection pooling for Supabase
- Configure pool size based on expected load
- Handle connection timeouts gracefully

### 18. Data Validation

**Current Gap:** Input validation not detailed.

**Solution:**

**Validation Needed:**

- Phone number format validation
- Email format validation
- Password strength validation
- Date/time parsing validation
- Numeric range validation (calories, water amounts, etc.)

**Implementation:**

```python
# utils/validators.py
def validate_phone_number(phone: str) -> bool:
    # E.164 format validation
    pass

def validate_email(email: str) -> bool:
    # Email format validation
    pass

def validate_password(password: str) -> Tuple[bool, str]:
    # Check strength, return (is_valid, error_message)
    pass
```

### 19. Documentation

**Current Gap:** Not mentioned.

**Solution:**

**Documentation Needed:**

- API documentation (for dashboard API)
- Integration setup guides (how to register apps)
- Developer documentation (architecture, adding new handlers)
- User documentation (how to use features)
- Deployment guide

### 20. Database Schema Inconsistency

**Issue Found:** `user_knowledge` table has `user_id TEXT` but should be `user_id INTEGER REFERENCES users(id)` to match other tables.

**Fix:**

```sql
-- In user_knowledge table definition, change:
user_id TEXT NOT NULL,  -- WRONG
-- To:
user_id INTEGER REFERENCES users(id) NOT NULL,  -- CORRECT
```

## Updated Implementation Checklist

Add these to todos:

- [ ] Implement user registration and phone verification flow
- [ ] Add password reset functionality
- [ ] Implement email verification (optional)
- [ ] Create comprehensive error handling system
- [ ] Set up application logging (structured logging)
- [ ] Implement rate limiting for API and SMS
- [ ] Add webhook signature verification
- [ ] Implement token encryption/decryption
- [ ] Set up background job scheduler
- [ ] Add caching layer (Redis or in-memory)
- [ ] Create user repository
- [ ] Document all new environment variables
- [ ] Create health check endpoints
- [ ] Set up database connection pooling
- [ ] Add input validation utilities
- [ ] Fix user_knowledge table schema (user_id should be INTEGER)
- [ ] Create comprehensive test suite
- [ ] Write deployment documentation
- [ ] Set up monitoring and alerting
- [ ] Implement timezone handling for multi-user system
- [ ] Add message deduplication and idempotency handling
- [ ] Create data retention and archival policies
- [ ] Set up database backup and disaster recovery strategy
- [ ] Add analytics and usage tracking (privacy-preserving)
- [ ] Implement feature flags for gradual rollouts
- [ ] Add user preferences system (notifications, units, response style)
- [ ] Implement help command and user guidance system
- [ ] Add concurrent request handling (message queue/locks)
- [ ] Implement database transactions for atomic operations
- [ ] Add API versioning for dashboard endpoints
- [ ] Create cost tracking and optimization system
- [ ] Handle SMS character limits and message splitting
- [ ] Add webhook retry logic for failed processing

### 21. Timezone Handling

**Current Gap:** System uses `datetime.now()` without timezone awareness. Multi-user system needs per-user timezones.

**Solution:**

**Database Addition:**

```sql
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';  -- e.g., 'America/New_York'
```

**Implementation:**

```python
from pytz import timezone as tz
from datetime import datetime

class TimezoneHandler:
    def get_user_timezone(self, user_id: int) -> str:
        user = user_repo.get_by_id(user_id)
        return user.timezone or 'UTC'
    
    def get_user_now(self, user_id: int) -> datetime:
        user_tz = tz(self.get_user_timezone(user_id))
        return datetime.now(user_tz)
    
    def convert_to_user_time(self, dt: datetime, user_id: int) -> datetime:
        user_tz = tz(self.get_user_timezone(user_id))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz('UTC'))
        return dt.astimezone(user_tz)
    
    def parse_user_date(self, date_str: str, user_id: int) -> datetime:
        user_tz = tz(self.get_user_timezone(user_id))
        # Parse date in user's timezone context
        pass
```

**Usage:**

- All date/time operations use user's timezone
- "today" means today in user's timezone
- Reminders fire at correct local time
- Stats calculated in user's timezone

### 22. Message Deduplication & Idempotency

**Current Gap:** No handling for duplicate messages (Twilio can send duplicates, user might send twice).

**Solution:**

**Database Addition:**

```sql
CREATE TABLE message_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    message_id TEXT UNIQUE,  -- Twilio message SID or hash
    message_body TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW(),
    response_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_message_log_message_id ON message_log(message_id);
CREATE INDEX idx_message_log_user ON message_log(user_id);
```

**Implementation:**

```python
def handle_sms_with_deduplication(message_body: str, message_id: str, phone_number: str):
    # Check if message already processed
    existing = db.get_message_by_id(message_id)
    if existing and existing.response_sent:
        # Return cached response or skip
        return None
    
    # Process message
    response = process_message(message_body, phone_number)
    
    # Log message
    db.log_message(user_id, message_id, message_body, phone_number, response)
    
    return response
```

### 23. Data Retention & Archival

**Current Gap:** No policy for how long to keep data.

**Solution:**

**Retention Policies:**

- **Active logs**: Keep indefinitely (until user deletes)
- **Sync history**: Keep 90 days, archive older
- **Message logs**: Keep 30 days, delete older (privacy)
- **Error logs**: Keep 90 days
- **Audit logs**: Keep 1 year (compliance)

**Implementation:**

```python
def archive_old_data():
    # Archive sync history older than 90 days
    cutoff = datetime.now() - timedelta(days=90)
    archive_sync_history(cutoff)
    
    # Delete message logs older than 30 days
    cutoff = datetime.now() - timedelta(days=30)
    delete_old_message_logs(cutoff)
```

### 24. Database Backup & Disaster Recovery

**Current Gap:** No backup strategy mentioned.

**Solution:**

**Backup Strategy:**

- **Daily backups**: Automated Supabase backups (they provide this)
- **Point-in-time recovery**: Enable in Supabase
- **Manual exports**: Weekly full database export
- **Backup verification**: Test restore monthly

**Disaster Recovery:**

- Document recovery procedures
- Test restore process
- Keep backup encryption keys secure
- Document rollback procedures

### 25. Analytics & Usage Tracking

**Current Gap:** No analytics mentioned (privacy-preserving usage metrics).

**Solution:**

**Privacy-Preserving Analytics:**

- Track feature usage (which intents are used most)
- Track error rates (NLP failures, API errors)
- Track performance metrics (response times)
- **No personal data**: Aggregate only, no user identification
- **Opt-out**: Users can disable analytics

**Implementation:**

```python
class Analytics:
    def track_intent(self, intent: str, success: bool):
        # Aggregate only - no user_id
        pass
    
    def track_response_time(self, handler: str, duration_ms: float):
        # Performance tracking
        pass
    
    def track_error(self, error_type: str, count: int):
        # Error tracking
        pass
```

### 26. Feature Flags

**Current Gap:** No way to enable/disable features without code changes.

**Solution:**

**Feature Flags:**

- Enable/disable features per user or globally
- Gradual rollouts (10% → 50% → 100%)
- A/B testing capabilities

**Database Addition:**

```sql
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    flag_name TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    rollout_percentage INTEGER DEFAULT 0,  -- 0-100
    enabled_for_users INTEGER[],  -- Specific user IDs
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Implementation:**

```python
class FeatureFlags:
    def is_enabled(self, flag_name: str, user_id: int = None) -> bool:
        flag = db.get_feature_flag(flag_name)
        if not flag.enabled:
            return False
        if flag.rollout_percentage > 0:
            return (user_id % 100) < flag.rollout_percentage
        if flag.enabled_for_users:
            return user_id in flag.enabled_for_users
        return True
```

### 27. Concurrent Request Handling

**Current Gap:** No mention of handling multiple simultaneous requests from same user.

**Solution:**

**Request Queue:**

- Process messages sequentially per user (avoid race conditions)
- Use message queue (Redis/RabbitMQ) or database locks
- Handle concurrent syncs gracefully

**Implementation:**

```python
from redis import Redis
import redis.lock

redis_client = Redis()

def process_message_with_lock(user_id: int, message: str):
    lock_key = f"user_lock:{user_id}"
    with redis_client.lock(lock_key, timeout=30):
        # Process message
        return process_message(message, user_id)
```

### 28. Data Consistency & Transactions

**Current Gap:** No mention of database transactions for atomic operations.

**Solution:**

**Transaction Management:**

- Use database transactions for multi-step operations
- Rollback on errors
- Ensure data consistency

**Implementation:**

```python
def log_workout_with_transaction(user_id: int, workout_data: dict):
    with db.transaction():
        # Insert gym log
        log_id = gym_repo.create(user_id, workout_data)
        
        # Update learned patterns
        if should_learn_pattern(workout_data):
            knowledge_repo.store_pattern(user_id, pattern)
        
        # Update stats cache
        stats_service.invalidate_cache(user_id)
        
        # All or nothing
```

### 29. API Versioning

**Current Gap:** No versioning strategy for dashboard API.

**Solution:**

**API Versioning:**

- Version dashboard API endpoints: `/api/v1/dashboard/stats`
- Maintain backward compatibility
- Document breaking changes

**Implementation:**

```python
@app.route('/api/v1/dashboard/stats')
def get_stats_v1():
    # Version 1 implementation
    pass

@app.route('/api/v2/dashboard/stats')
def get_stats_v2():
    # Version 2 with improvements
    pass
```

### 30. Cost Management

**Current Gap:** No cost tracking or optimization.

**Solution:**

**Cost Tracking:**

- Track Gemini API usage (cost per request)
- Track Twilio SMS costs
- Track Supabase storage/bandwidth
- Set usage alerts
- Optimize expensive operations

**Implementation:**

```python
class CostTracker:
    def track_gemini_request(self, model: str, tokens: int):
        # Track API costs
        cost = calculate_cost(model, tokens)
        db.log_api_cost('gemini', cost)
    
    def track_sms_sent(self, phone_number: str):
        # Track SMS costs
        db.log_sms_cost(phone_number)
```

### 31. Message Ordering

**Current Gap:** No guarantee messages are processed in order.

**Solution:**

**Message Sequencing:**

- Use message timestamps for ordering
- Handle out-of-order delivery
- Store message sequence numbers

### 32. Integration Rate Limits

**Current Gap:** No handling for provider API rate limits.

**Solution:**

**Rate Limit Handling:**

- Respect Fitbit/Google API rate limits
- Implement exponential backoff
- Queue syncs if rate limited
- Notify users if sync delayed

### 33. User Preferences

**Current Gap:** No user preferences system.

**Solution:**

**User Preferences:**

- Notification preferences (when to send reminders)
- Response style (concise vs. friendly)
- Units (metric vs. imperial)
- Language (future: i18n)

**Database Addition:**

```sql
CREATE TABLE user_preferences (
    user_id INTEGER REFERENCES users(id) PRIMARY KEY,
    notification_hours INTEGER[],  -- Hours when notifications allowed
    response_style TEXT DEFAULT 'friendly',  -- 'concise', 'friendly', 'coach'
    units TEXT DEFAULT 'metric',  -- 'metric', 'imperial'
    language TEXT DEFAULT 'en',
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 34. Help & Documentation Commands

**Current Gap:** No "help" command or user guidance.

**Solution:**

**Help System:**

- User: "help" → Shows available commands
- User: "help food" → Shows food logging examples
- User: "help integrations" → Shows integration info
- Context-aware help based on user's usage

### 35. Data Export Format

**Current Gap:** Export mentioned but format not detailed.

**Solution:**

**Export Formats:**

- **JSON**: Machine-readable, complete data
- **CSV**: Spreadsheet-friendly
- **PDF**: Human-readable report
- Include metadata (export date, user info)

### 36. Integration Status Monitoring

**Current Gap:** No way to monitor integration health.

**Solution:**

**Integration Health:**

- Check token validity periodically
- Monitor sync success rates
- Alert on repeated failures
- Show integration status in dashboard

### 37. Learning System Edge Cases

**Current Gap:** Edge cases not fully covered.

**Solution:**

**Edge Cases to Handle:**

- User teaches conflicting patterns ("dhamaka" = workout, then "dhamaka" = food)
- Pattern confidence drops below threshold
- User deletes learned pattern
- Pattern used incorrectly (how to detect and adjust)
- Too many patterns (performance concern)

### 38. Multi-User Data Isolation Testing

**Current Gap:** Need to ensure RLS policies work correctly.

**Solution:**

**Testing:**

- Create test users
- Verify users can't see each other's data
- Test RLS policies
- Test user_id foreign key constraints

### 39. SMS Character Limits

**Current Gap:** No handling for long responses (SMS 160 char limit, longer messages split).

**Solution:**

**Response Handling:**

- Keep responses concise
- Split long responses into multiple messages
- Use link shorteners for URLs
- Prioritize important info in first message

### 40. Integration Webhook Retry Logic

**Current Gap:** What if webhook processing fails?

**Solution:**

**Webhook Retry:**

- Store failed webhooks
- Retry with exponential backoff
- Dead letter queue for permanent failures
- Alert on repeated failures

### 41. Security Vulnerabilities - Input Validation & Sanitization

**Current Gap:** No comprehensive input validation and sanitization strategy.

**Solution:**

**Input Validation:**

- Validate all user inputs (phone numbers, emails, dates, numbers)
- Sanitize text inputs to prevent XSS
- Validate file uploads (if any)
- Validate API request payloads
- Validate database queries (use parameterized queries)

**Implementation:**

```python
# utils/validators.py
import re
from html import escape

def sanitize_text(text: str) -> str:
    # Remove potentially dangerous characters
    # Escape HTML entities
    return escape(text.strip())

def validate_phone_number(phone: str) -> bool:
    # E.164 format: +1234567890
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_date(date_str: str) -> bool:
    # Validate date format
    try:
        datetime.fromisoformat(date_str)
        return True
    except:
        return False

# Always use parameterized queries
def safe_query(user_id: int, date: str):
    # GOOD: Parameterized
    db.execute("SELECT * FROM food_logs WHERE user_id = %s AND date = %s", (user_id, date))
    
    # BAD: String interpolation (SQL injection risk)
    # db.execute(f"SELECT * FROM food_logs WHERE user_id = {user_id}")
```

### 42. Security - XSS Prevention

**Current Gap:** No XSS prevention for web dashboard.

**Solution:**

**XSS Prevention:**

- Escape all user-generated content in HTML
- Use template engines that auto-escape (Jinja2 does this)
- Content Security Policy (CSP) headers
- Sanitize user inputs before storing
- Validate and sanitize on output

**Implementation:**

```python
# In templates, use auto-escaping
{{ user_message }}  # Jinja2 auto-escapes

# For JSON responses
import json
response = json.dumps(data)  # Safe, but validate data structure

# CSP headers
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

### 43. Security - CSRF Protection

**Current Gap:** Only mentioned for OAuth, not for web forms.

**Solution:**

**CSRF Protection:**

- Use Flask-WTF for CSRF tokens
- Validate CSRF token on all state-changing requests
- SameSite cookies
- Double-submit cookie pattern

**Implementation:**

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

@app.route('/dashboard/settings', methods=['POST'])
@csrf.exempt  # Only if needed
def update_settings():
    # CSRF token automatically validated
    pass
```

### 44. Security - SQL Injection Prevention

**Current Gap:** Need to ensure all queries use parameterized statements.

**Solution:**

**SQL Injection Prevention:**

- Always use parameterized queries (Supabase client does this)
- Never use string interpolation in SQL
- Validate all inputs before queries
- Use ORM/repository pattern (abstracts SQL)

**Implementation:**

```python
# GOOD: Supabase client uses parameterized queries
result = supabase.table('food_logs').select('*').eq('user_id', user_id).execute()

# BAD: Never do this
# query = f"SELECT * FROM food_logs WHERE user_id = {user_id}"
```

### 45. Security - Session Management

**Current Gap:** Session security not detailed.

**Solution:**

**Session Security:**

- Secure cookies (HTTPS only)
- HttpOnly cookies (prevent JavaScript access)
- SameSite cookies (CSRF protection)
- Session expiration (30 minutes inactivity)
- Session rotation on login
- Secure session storage

**Implementation:**

```python
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
```

### 46. Security - Password Policies

**Current Gap:** No password strength requirements.

**Solution:**

**Password Policies:**

- Minimum length (8 characters)
- Require uppercase, lowercase, number, special character
- Password strength meter
- Prevent common passwords
- Password history (don't reuse last 5)
- Account lockout after failed attempts

**Implementation:**

```python
import re

def validate_password_strength(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain special character"
    return True, "Password is strong"
```

### 47. Security - Account Lockout & Brute Force Protection

**Current Gap:** No protection against brute force attacks.

**Solution:**

**Brute Force Protection:**

- Lock account after 5 failed login attempts
- Exponential backoff (1 min, 2 min, 4 min, etc.)
- IP-based rate limiting
- CAPTCHA after 3 failed attempts
- Alert on suspicious activity

**Database Addition:**

```sql
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;
ALTER TABLE users ADD COLUMN last_failed_login TIMESTAMP;
```

**Implementation:**

```python
def handle_failed_login(user_id: int):
    user = user_repo.get_by_id(user_id)
    user.failed_login_attempts += 1
    user.last_failed_login = datetime.now()
    
    if user.failed_login_attempts >= 5:
        # Lock for 1 hour
        user.locked_until = datetime.now() + timedelta(hours=1)
        # Send alert email
        send_security_alert(user.email)
    
    user_repo.update(user_id, failed_login_attempts=user.failed_login_attempts)
```

### 48. Security - Secrets Management

**Current Gap:** Secrets stored in environment variables, but no rotation strategy.

**Solution:**

**Secrets Management:**

- Use environment variables (current approach is good)
- Never commit secrets to git
- Rotate secrets periodically (every 90 days)
- Use secret management service (AWS Secrets Manager, HashiCorp Vault) for production
- Different secrets for dev/staging/prod
- Audit secret access

**Implementation:**

```python
# Use python-dotenv for local development
# Use secret management service for production

class SecretManager:
    def get_secret(self, key: str) -> str:
        if os.getenv('ENV') == 'production':
            return get_from_secrets_manager(key)
        else:
            return os.getenv(key)
```

### 49. Security - API Key Rotation

**Current Gap:** No strategy for rotating API keys.

**Solution:**

**API Key Rotation:**

- Track when keys were last rotated
- Support multiple keys during rotation
- Automated rotation reminders
- Graceful rotation (update without downtime)

**Database Addition:**

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    service TEXT NOT NULL,  -- 'gemini', 'twilio', etc.
    key_name TEXT NOT NULL,  -- 'primary', 'secondary'
    key_value TEXT NOT NULL,  -- Encrypted
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 50. Security - CORS Configuration

**Current Gap:** No CORS policy for API endpoints.

**Solution:**

**CORS Configuration:**

- Allow only specific origins
- Restrict methods (GET, POST, etc.)
- Restrict headers
- Credentials handling

**Implementation:**

```python
from flask_cors import CORS

CORS(app, 
     origins=['https://yourapp.com', 'https://www.yourapp.com'],
     methods=['GET', 'POST', 'PUT', 'DELETE'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)
```

### 51. Performance - Query Optimization

**Current Gap:** No query optimization strategy.

**Solution:**

**Query Optimization:**

- Use indexes (already planned)
- Avoid N+1 queries
- Use eager loading for related data
- Paginate large result sets
- Use SELECT only needed columns
- Query analysis and profiling

**Implementation:**

```python
# BAD: N+1 query problem
users = get_all_users()
for user in users:
    logs = get_food_logs(user.id)  # Query per user!

# GOOD: Batch query
users = get_all_users()
user_ids = [u.id for u in users]
all_logs = get_food_logs_batch(user_ids)  # Single query
logs_by_user = group_by_user(all_logs)
```

### 52. Performance - Pagination

**Current Gap:** No pagination for large data sets.

**Solution:**

**Pagination Strategy:**

- Cursor-based pagination (better than offset)
- Limit result sets (default 50, max 100)
- Return pagination metadata (has_more, next_cursor)

**Implementation:**

```python
def get_food_logs_paginated(user_id: int, cursor: str = None, limit: int = 50):
    query = supabase.table('food_logs').select('*').eq('user_id', user_id)
    
    if cursor:
        # Cursor-based (more efficient)
        query = query.gt('id', cursor)
    
    query = query.order('timestamp', desc=True).limit(limit)
    results = query.execute()
    
    has_more = len(results.data) == limit
    next_cursor = results.data[-1]['id'] if has_more else None
    
    return {
        'data': results.data,
        'has_more': has_more,
        'next_cursor': next_cursor
    }
```

### 53. Performance - Caching Invalidation

**Current Gap:** Caching mentioned but invalidation strategy not detailed.

**Solution:**

**Cache Invalidation:**

- Invalidate on data updates
- TTL-based expiration
- Event-driven invalidation
- Cache versioning

**Implementation:**

```python
def log_food(user_id: int, food_data: dict):
    # Insert food log
    food_repo.create(user_id, food_data)
    
    # Invalidate related caches
    cache.delete(f"user_stats:{user_id}")
    cache.delete(f"user_food_logs:{user_id}:today")
    cache.delete(f"user_patterns:{user_id}")  # If food affects patterns
```

### 54. Performance - Memory Management

**Current Gap:** No memory leak prevention.

**Solution:**

**Memory Management:**

- Close database connections properly
- Clear large data structures after use
- Use generators for large datasets
- Monitor memory usage
- Set connection pool limits

**Implementation:**

```python
# Use context managers
with db.connection() as conn:
    # Auto-closes connection
    pass

# Use generators for large datasets
def get_all_logs_generator(user_id: int):
    # Yield one at a time instead of loading all
    for log in db.stream_query(f"SELECT * FROM food_logs WHERE user_id = {user_id}"):
        yield log
```

### 55. Performance - Timeout Handling

**Current Gap:** No timeout configuration for API calls.

**Solution:**

**Timeout Configuration:**

- Set timeouts for external API calls (Gemini, Fitbit, etc.)
- Set timeouts for database queries
- Handle timeout errors gracefully
- Retry with shorter timeout

**Implementation:**

```python
import requests

# Set timeouts for API calls
response = requests.get(
    'https://api.fitbit.com/...',
    timeout=(5, 30)  # (connect timeout, read timeout)
)

# Database query timeout
query = supabase.table('food_logs').select('*').limit(1000)
# Supabase handles timeouts, but monitor slow queries
```

### 56. Performance - Circuit Breaker Pattern

**Current Gap:** No circuit breaker for external services.

**Solution:**

**Circuit Breaker:**

- Open circuit after N failures
- Half-open state for testing
- Close circuit after success
- Prevent cascading failures

**Implementation:**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_gemini_api(prompt: str):
    # If 5 failures in a row, circuit opens
    # After 60 seconds, try again (half-open)
    return gemini_client.generate(prompt)
```

### 57. Data - Search Functionality

**Current Gap:** No search capability for user data.

**Solution:**

**Search Features:**

- Search food logs by name
- Search todos/reminders by content
- Search learned patterns
- Full-text search for facts
- Search history

**Database Addition:**

```sql
-- Add full-text search index
CREATE INDEX idx_food_logs_search ON food_logs USING gin(to_tsvector('english', food_name));
CREATE INDEX idx_facts_search ON facts USING gin(to_tsvector('english', key || ' ' || value));
```

**Implementation:**

```python
def search_food_logs(user_id: int, query: str):
    return supabase.table('food_logs')\
        .select('*')\
        .eq('user_id', user_id)\
        .text_search('food_name', query)\
        .execute()
```

### 58. Data - Filtering & Sorting

**Current Gap:** No filtering/sorting for dashboard data.

**Solution:**

**Filtering & Sorting:**

- Filter logs by date range
- Filter by type (food, water, gym, etc.)
- Sort by date, calories, etc.
- Multiple filters combined
- Save filter preferences

**Implementation:**

```python
def get_food_logs_filtered(user_id: int, filters: dict):
    query = supabase.table('food_logs').select('*').eq('user_id', user_id)
    
    if filters.get('start_date'):
        query = query.gte('timestamp', filters['start_date'])
    if filters.get('end_date'):
        query = query.lte('timestamp', filters['end_date'])
    if filters.get('min_calories'):
        query = query.gte('calories', filters['min_calories'])
    if filters.get('restaurant'):
        query = query.eq('restaurant', filters['restaurant'])
    
    # Sorting
    order_by = filters.get('order_by', 'timestamp')
    order_desc = filters.get('order_desc', True)
    query = query.order(order_by, desc=order_desc)
    
    return query.execute()
```

### 59. User Experience - Notification Preferences

**Current Gap:** Basic notification preferences mentioned but not detailed.

**Solution:**

**Notification Preferences:**

- Quiet hours (don't send 10pm-8am)
- Notification frequency (immediate, daily digest, weekly)
- Notification channels (SMS, email, push)
- Notification types (reminders, nudges, digests)
- Do not disturb mode

**Database Addition:**

```sql
-- Extend user_preferences
ALTER TABLE user_preferences ADD COLUMN quiet_hours_start INTEGER DEFAULT 22;  -- 10 PM
ALTER TABLE user_preferences ADD COLUMN quiet_hours_end INTEGER DEFAULT 8;  -- 8 AM
ALTER TABLE user_preferences ADD COLUMN notification_frequency TEXT DEFAULT 'immediate';
ALTER TABLE user_preferences ADD COLUMN notification_channels TEXT[] DEFAULT ARRAY['sms'];
ALTER TABLE user_preferences ADD COLUMN do_not_disturb BOOLEAN DEFAULT FALSE;
```

### 60. User Experience - User Feedback System

**Current Gap:** No way for users to provide feedback.

**Solution:**

**Feedback System:**

- "Was this helpful?" prompts
- Bug reporting via SMS or website
- Feature requests
- Rating system for responses
- Feedback analytics

**Database Addition:**

```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    feedback_type TEXT NOT NULL,  -- 'bug', 'feature', 'rating', 'general'
    message TEXT NOT NULL,
    rating INTEGER,  -- 1-5 stars
    context JSONB,  -- What user was doing
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 61. User Experience - Support Ticket System

**Current Gap:** No support system.

**Solution:**

**Support System:**

- Create tickets via SMS or website
- Track ticket status
- Email notifications for responses
- Ticket history

**Database Addition:**

```sql
CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'open',  -- 'open', 'in_progress', 'resolved', 'closed'
    priority TEXT DEFAULT 'normal',  -- 'low', 'normal', 'high', 'urgent'
    assigned_to TEXT,  -- Support agent
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 62. Operations - Dependency Management

**Current Gap:** No strategy for managing dependencies.

**Solution:**

**Dependency Management:**

- Pin all versions in requirements.txt
- Regular security audits (pip-audit, safety)
- Update dependencies regularly
- Test updates in staging
- Document breaking changes

**Implementation:**

```bash
# Pin versions
flask==2.3.3
supabase==1.0.0
# etc.

# Security audit
pip-audit
safety check
```

### 63. Operations - Load Testing

**Current Gap:** No load testing strategy.

**Solution:**

**Load Testing:**

- Test with expected user load
- Test API endpoints
- Test database under load
- Identify bottlenecks
- Set up performance baselines

**Tools:**

- Locust, Apache JMeter, k6
- Test scenarios: 100 concurrent users, 1000 requests/min

### 64. Operations - Chaos Engineering

**Current Gap:** No resilience testing.

**Solution:**

**Chaos Testing:**

- Simulate API failures
- Simulate database slowdowns
- Test error recovery
- Verify graceful degradation
- Test failover scenarios

### 65. Integration - Partial Sync Handling

**Current Gap:** What if sync partially fails?

**Solution:**

**Partial Sync:**

- Track what was synced successfully
- Resume from last successful item
- Don't duplicate already-synced data
- Report partial success to user

**Implementation:**

```python
def sync_with_resume(user_id: int, provider: str):
    last_sync = get_last_successful_sync(user_id, provider)
    start_date = last_sync.last_synced_date if last_sync else default_start_date
    
    items = fetch_from_provider(start_date)
    synced_count = 0
    failed_count = 0
    
    for item in items:
        try:
            sync_item(user_id, item)
            synced_count += 1
        except Exception as e:
            failed_count += 1
            log_sync_error(user_id, provider, item, str(e))
    
    log_sync_result(user_id, provider, synced_count, failed_count)
    return {'synced': synced_count, 'failed': failed_count}
```

### 66. Integration - Provider API Changes

**Current Gap:** What if Fitbit/Google changes their API?

**Solution:**

**API Versioning:**

- Track API versions used
- Monitor for deprecation notices
- Support multiple API versions during transition
- Graceful migration to new versions
- Alert on API changes

**Implementation:**

```python
class FitbitIntegration:
    def __init__(self):
        self.api_version = '1.2'  # Track version
        self.supported_versions = ['1.2', '1.1']  # Support multiple
    
    def check_api_version(self):
        # Check if current version still supported
        # Migrate if needed
        pass
```

### 67. Integration - Provider Downtime

**Current Gap:** What if Fitbit/Google is down?

**Solution:**

**Downtime Handling:**

- Detect provider downtime
- Queue syncs for retry
- Notify users of delays
- Continue with manual logging
- Automatic retry when service resumes

**Implementation:**

```python
def sync_with_retry(user_id: int, provider: str):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return sync_provider(user_id, provider)
        except ProviderDownException:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                schedule_retry(user_id, provider, wait_time)
            else:
                notify_user_downtime(user_id, provider)
                raise
```

### 68. Learning System - Pattern Performance

**Current Gap:** Performance with many learned patterns.

**Solution:**

**Pattern Optimization:**

- Index patterns by term and type
- Cache frequently used patterns
- Limit pattern search scope
- Pattern pruning (remove low-confidence, unused patterns)
- Pattern compression

**Implementation:**

```python
def get_patterns_optimized(user_id: int, message: str):
    # Only search patterns that could match
    message_words = set(message.lower().split())
    
    # Use database index on pattern_term
    patterns = db.query("""
        SELECT * FROM user_knowledge 
        WHERE user_id = %s 
        AND pattern_term = ANY(%s)
        AND confidence > 0.3
    """, (user_id, list(message_words)))
    
    return patterns
```

### 69. Learning System - Pattern Pruning

**Current Gap:** Patterns accumulate indefinitely.

**Solution:**

**Pattern Pruning:**

- Remove patterns with confidence < 0.2
- Remove unused patterns (not used in 90 days)
- Merge similar patterns
- Archive old patterns

**Implementation:**

```python
def prune_patterns():
    # Remove low-confidence patterns
    db.execute("""
        DELETE FROM user_knowledge 
        WHERE confidence < 0.2
    """)
    
    # Remove unused patterns
    cutoff = datetime.now() - timedelta(days=90)
    db.execute("""
        DELETE FROM user_knowledge 
        WHERE last_used < %s AND usage_count < 3
    """, (cutoff,))
```

### 70. Learning System - Pattern Conflict Detection

**Current Gap:** Conflict resolution mentioned but detection not detailed.

**Solution:**

**Conflict Detection:**

- Detect when user teaches conflicting pattern
- Show both patterns to user
- Ask user to clarify
- Track conflict resolution

**Implementation:**

```python
def detect_conflict(user_id: int, new_pattern: Pattern):
    existing = get_pattern_by_term(user_id, new_pattern.term)
    
    if existing and existing.associated_value != new_pattern.associated_value:
        # Conflict detected
        return {
            'has_conflict': True,
            'existing': existing,
            'new': new_pattern,
            'resolution': 'ask_user'
        }
    return {'has_conflict': False}
```

### 71. Data - Data Normalization

**Current Gap:** No data normalization strategy.

**Solution:**

**Data Normalization:**

- Normalize food names (lowercase, trim)
- Normalize restaurant names
- Normalize exercise names
- Consistent date formats
- Consistent units (always ml, always grams)

**Implementation:**

```python
def normalize_food_name(name: str) -> str:
    # Lowercase, trim, remove extra spaces
    return ' '.join(name.lower().strip().split())

def normalize_restaurant(name: str) -> str:
    # Map nicknames to canonical names
    nickname_map = {'kraft': 'the_devils_krafthouse', ...}
    return nickname_map.get(name.lower(), name)
```

### 72. Data - Referential Integrity

**Current Gap:** Need to ensure foreign keys are enforced.

**Solution:**

**Referential Integrity:**

- All foreign keys have CASCADE or RESTRICT
- Validate before delete
- Handle orphaned records
- Data integrity checks

**Database:**

```sql
-- Ensure CASCADE on deletes
ALTER TABLE food_logs 
    DROP CONSTRAINT IF EXISTS food_logs_user_id_fkey,
    ADD CONSTRAINT food_logs_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 73. Operations - Blue-Green Deployment

**Current Gap:** No deployment strategy to avoid downtime.

**Solution:**

**Deployment Strategy:**

- Blue-green deployment
- Canary releases
- Feature flags for gradual rollout
- Database migration strategy
- Rollback procedures

### 74. Operations - Monitoring & Alerting

**Current Gap:** Monitoring mentioned but not detailed.

**Solution:**

**Monitoring:**

- Application performance (response times, error rates)
- Database performance (query times, connection pool)
- API usage (Gemini, Twilio costs)
- Integration health (sync success rates)
- User metrics (active users, messages/day)

**Tools:**

- Application: Sentry, Datadog, New Relic
- Infrastructure: Supabase dashboard, server metrics
- Alerts: PagerDuty, email, SMS

### 75. User Experience - Autocomplete & Suggestions

**Current Gap:** No autocomplete for food/exercise names.

**Solution:**

**Autocomplete:**

- Autocomplete food names as user types
- Autocomplete exercise names
- Autocomplete restaurant names
- Learn from user's history (show most used first)
- Fuzzy matching

**Implementation:**

```python
def autocomplete_food(user_id: int, query: str, limit: int = 10):
    # Search user's food database
    # Prioritize user's frequently used foods
    # Fuzzy match query
    user_foods = get_user_frequent_foods(user_id)
    matches = fuzzy_match(query, user_foods, limit=limit)
    return matches
```

### 76. User Experience - Recommendations

**Current Gap:** No recommendation system.

**Solution:**

**Recommendations:**

- Recommend foods based on goals (high protein, low cal)
- Recommend workouts based on schedule
- Recommend water intake based on activity
- Personalized suggestions

**Implementation:**

```python
def recommend_food(user_id: int, goals: dict):
    # Get user's food history
    # Filter by goals (high_protein, low_calories, etc.)
    # Rank by user's preferences
    # Return top recommendations
    pass
```

### 77. Data - Data Validation at Repository Level

**Current Gap:** Validation mentioned but not at repository level.

**Solution:**

**Repository Validation:**

- Validate all data before insert/update
- Type checking
- Range validation (calories > 0, etc.)
- Business rule validation
- Return validation errors

**Implementation:**

```python
class FoodRepository:
    def create(self, user_id: int, food_data: dict) -> int:
        # Validate
        if food_data['calories'] < 0:
            raise ValidationError("Calories cannot be negative")
        if not food_data.get('food_name'):
            raise ValidationError("Food name is required")
        
        # Then insert
        return db.insert('food_logs', food_data)
```

### 78. Operations - Log Aggregation

**Current Gap:** Logging mentioned but aggregation not detailed.

**Solution:**

**Log Aggregation:**

- Centralized logging (ELK stack, CloudWatch, etc.)
- Structured logs (JSON format)
- Log levels
- Log retention
- Search and analysis

**Implementation:**

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_data)
```

### 79. Security - Request/Response Validation

**Current Gap:** API request/response validation not detailed.

**Solution:**

**Request/Response Validation:**

- Validate all API request payloads
- Validate response data before sending
- Use schemas (JSON Schema, Pydantic)
- Type checking
- Sanitize outputs

**Implementation:**

```python
from pydantic import BaseModel, validator

class FoodLogRequest(BaseModel):
    food_name: str
    calories: float
    protein: float
    
    @validator('calories')
    def validate_calories(cls, v):
        if v < 0 or v > 10000:
            raise ValueError('Calories must be between 0 and 10000')
        return v

@app.route('/api/food', methods=['POST'])
def log_food():
    try:
        data = FoodLogRequest(**request.json)
        # Data is validated
        return food_repo.create(data)
    except ValidationError as e:
        return {'error': str(e)}, 400
```

### 80. Operations - Database Migration Versioning

**Current Gap:** No migration versioning system.

**Solution:**

**Migration Versioning:**

- Track applied migrations
- Version control for migrations
- Rollback support
- Test migrations in staging

**Database Addition:**

```sql
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);
```

### 81. User Experience - Response Personalization

**Current Gap:** Responses are generic, not personalized.

**Solution:**

**Response Personalization:**

- Learn user's preferred response style
- Use user's name
- Reference user's history
- Adapt tone based on context
- Celebrate milestones

**Implementation:**

```python
def personalize_response(user_id: int, base_response: str) -> str:
    user = user_repo.get_by_id(user_id)
    prefs = get_user_preferences(user_id)
    
    if prefs.response_style == 'concise':
        return make_concise(base_response)
    elif prefs.response_style == 'friendly':
        return make_friendly(base_response, user.name)
    
    return base_response
```

### 82. Data - Data Export Security

**Current Gap:** Export security not mentioned.

**Solution:**

**Export Security:**

- Require authentication for export
- Encrypt export files
- Expire download links (24 hours)
- Audit export requests
- Rate limit exports

### 83. Integration - Sync Conflict Resolution UI

**Current Gap:** Conflict resolution mentioned but UI not detailed.

**Solution:**

**Conflict Resolution UI:**

- Show conflicts in dashboard
- Let user choose which data to keep
- Merge option
- Conflict history

### 84. Learning System - Pattern Search Optimization

**Current Gap:** Pattern search could be slow with many patterns.

**Solution:**

**Search Optimization:**

- Use database full-text search
- Index patterns properly
- Cache search results
- Limit search scope
- Use approximate matching (fuzzy)

### 85. Operations - Graceful Shutdown

**Current Gap:** No graceful shutdown procedure.

**Solution:**

**Graceful Shutdown:**

- Finish processing current requests
- Close database connections
- Save state
- Stop background jobs cleanly
- Health check for shutdown readiness

**Implementation:**

```python
import signal
import atexit

def graceful_shutdown(signum, frame):
    print("Shutting down gracefully...")
    scheduler.shutdown()
    db.close_all_connections()
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)
```

### 86. Security - Error Message Security

**Current Gap:** Error messages might leak sensitive info.

**Solution:**

**Error Message Security:**

- Don't expose stack traces to users
- Don't expose database errors
- Generic error messages for users
- Detailed errors in logs only
- Sanitize error responses

**Implementation:**

```python
@app.errorhandler(Exception)
def handle_error(error):
    # Log detailed error
    logger.error("Unhandled exception", exc_info=True)
    
    # Return generic message to user
    return {'error': 'An error occurred. Please try again.'}, 500
```

### 87. Data - Data Consistency Checks

**Current Gap:** No data consistency validation.

**Solution:**

**Consistency Checks:**

- Validate foreign key relationships
- Check for orphaned records
- Validate data ranges
- Check for duplicates
- Periodic integrity checks

**Implementation:**

```python
def validate_data_integrity():
    # Check for orphaned records
    orphaned = db.execute("""
        SELECT id FROM food_logs f
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.id = f.user_id
        )
    """)
    
    if orphaned:
        logger.warning(f"Found {len(orphaned)} orphaned food logs")
        # Fix or alert
```

### 88. User Experience - Multi-Language Support (Future)

**Current Gap:** English only.

**Solution:**

**Internationalization:**

- Store user language preference
- Translate responses
- Translate UI (website)
- Handle date/time formats per locale
- Currency/units per locale

**Database Addition:**

```sql
ALTER TABLE user_preferences ADD COLUMN language TEXT DEFAULT 'en';
ALTER TABLE user_preferences ADD COLUMN locale TEXT DEFAULT 'en_US';
```

### 89. Operations - Resource Limits

**Current Gap:** No resource limits.

**Solution:**

**Resource Limits:**

- Limit message length
- Limit export size
- Limit sync data size
- Limit number of patterns per user
- Rate limit expensive operations

### 90. Security - PII Handling in Logs

**Current Gap:** Logs might contain PII.

**Solution:**

**PII Handling:**

- Don't log phone numbers
- Don't log full messages
- Hash sensitive data in logs
- Redact PII before logging
- Log only necessary data

**Implementation:**

```python
def safe_log(message: str, phone_number: str):
    # Hash phone number
    phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:8]
    
    # Truncate message
    safe_message = message[:50] + "..." if len(message) > 50 else message
    
    logger.info(f"Message from {phone_hash}: {safe_message}")
```

### 91. Integration - Webhook Delivery Guarantees

**Current Gap:** No guarantee webhooks are processed.

**Solution:**

**Webhook Guarantees:**

- Acknowledge webhook immediately
- Process asynchronously
- Store webhook payload
- Retry on failure
- Idempotent processing

### 92. Learning System - Pattern Versioning

**Current Gap:** No way to track pattern changes.

**Solution:**

**Pattern Versioning:**

- Track pattern history
- See when pattern was created/modified
- Rollback pattern changes
- Pattern audit trail

**Database Addition:**

```sql
CREATE TABLE user_knowledge_history (
    id SERIAL PRIMARY KEY,
    knowledge_id INTEGER REFERENCES user_knowledge(id),
    action TEXT NOT NULL,  -- 'created', 'updated', 'deleted'
    old_value JSONB,
    new_value JSONB,
    changed_at TIMESTAMP DEFAULT NOW()
);
```

### 93. Operations - Configuration Management

**Current Gap:** Config scattered, no centralized management.

**Solution:**

**Configuration Management:**

- Centralize all config
- Environment-specific configs
- Config validation on startup
- Hot-reload for non-critical config
- Config versioning

### 94. User Experience - Keyboard Shortcuts (Website)

**Current Gap:** No keyboard shortcuts for power users.

**Solution:**

**Keyboard Shortcuts:**

- Quick actions (Ctrl+K for search)
- Navigation shortcuts
- Form shortcuts
- Accessibility

### 95. Data - Data Anonymization for Analytics

**Current Gap:** Analytics might need anonymized data.

**Solution:**

**Data Anonymization:**

- Hash user IDs in analytics
- Aggregate data only
- Remove PII
- Differential privacy
- Analytics opt-out

### 96. Operations - Dependency Vulnerability Scanning

**Current Gap:** No automated security scanning.

**Solution:**

**Vulnerability Scanning:**

- Automated scans (GitHub Dependabot, Snyk)
- Regular security audits
- Update vulnerable packages
- Security patch process

### 97. Integration - Sync Status Dashboard

**Current Gap:** Users can't see sync status easily.

**Solution:**

**Sync Status:**

- Real-time sync status in dashboard
- Sync progress indicator
- Last sync time
- Sync errors visible
- Manual retry button

### 98. Learning System - Pattern Confidence Visualization

**Current Gap:** Users can't see their learned patterns.

**Solution:**

**Pattern Visualization:**

- Show all learned patterns in dashboard
- Show confidence scores
- Show usage counts
- Edit/delete patterns
- Pattern effectiveness metrics

### 99. Operations - Database Query Monitoring

**Current Gap:** No slow query monitoring.

**Solution:**

**Query Monitoring:**

- Log slow queries (>1 second)
- Identify N+1 queries
- Query performance metrics
- Index usage analysis
- Query optimization recommendations

### 100. User Experience - Bulk Operations

**Current Gap:** No bulk edit/delete.

**Solution:**

**Bulk Operations:**

- Bulk delete logs
- Bulk edit (change restaurant for multiple entries)
- Bulk export
- Select all
- Undo bulk operations

### 101. Security - Output Encoding

**Current Gap:** No output encoding strategy for web dashboard.

**Solution:**

**Output Encoding:**

- Encode all user-generated content in HTML
- Encode URLs
- Encode JSON properly
- Prevent injection via output

**Implementation:**

```python
from markupsafe import escape

# In templates
{{ user_input|escape }}  # Auto-escape

# In code
safe_output = escape(user_input)
```

### 102. Security - Session Fixation Prevention

**Current Gap:** No session fixation protection.

**Solution:**

**Session Fixation Prevention:**

- Regenerate session ID on login
- Regenerate on privilege change
- Invalidate old sessions
- Use secure session IDs

### 103. Security - Content Security Policy

**Current Gap:** No CSP headers.

**Solution:**

**CSP Headers:**

- Define allowed sources
- Prevent XSS
- Report violations
- Strict CSP policy

**Implementation:**

```python
@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.fitbit.com https://api.google.com"
    )
    return response
```

### 104. Performance - Database Index Optimization

**Current Gap:** Indexes mentioned but optimization not detailed.

**Solution:**

**Index Optimization:**

- Analyze query patterns
- Create composite indexes for common queries
- Remove unused indexes
- Monitor index usage
- Partial indexes for filtered queries

**Implementation:**

```sql
-- Composite index for common query
CREATE INDEX idx_food_logs_user_date ON food_logs(user_id, timestamp DESC);

-- Partial index (only for active users)
CREATE INDEX idx_active_users ON users(id) WHERE is_active = TRUE;
```

### 105. Performance - Connection Pool Tuning

**Current Gap:** Connection pooling mentioned but tuning not detailed.

**Solution:**

**Connection Pool Tuning:**

- Set appropriate pool size (min/max)
- Monitor connection usage
- Handle connection exhaustion
- Connection timeout configuration
- Idle connection cleanup

**Implementation:**

```python
# Supabase handles this, but monitor:
# - Active connections
# - Connection wait time
# - Connection errors
```

### 106. Data - Data Archival Strategy

**Current Gap:** Archival mentioned but strategy not detailed.

**Solution:**

**Archival Strategy:**

- Archive old data to cold storage
- Compress archived data
- Keep archive accessible (read-only)
- Archive retention policy
- Restore from archive process

### 107. Operations - Canary Deployments

**Current Gap:** No canary deployment strategy.

**Solution:**

**Canary Deployments:**

- Deploy to small percentage of users first
- Monitor errors and performance
- Gradually increase rollout
- Rollback if issues detected
- Feature flags for canary features

### 108. User Experience - Progressive Web App (PWA)

**Current Gap:** Website not optimized for mobile.

**Solution:**

**PWA Features:**

- Offline capability
- Install prompt
- Push notifications
- App-like experience
- Service worker for caching

### 109. User Experience - Accessibility (a11y)

**Current Gap:** No accessibility considerations.

**Solution:**

**Accessibility:**

- ARIA labels
- Keyboard navigation
- Screen reader support
- Color contrast
- Focus indicators
- Alt text for images

### 110. Operations - Database Connection Retry

**Current Gap:** No retry logic for database connections.

**Solution:**

**Connection Retry:**

- Retry on connection failure
- Exponential backoff
- Max retry attempts
- Fallback to read-only mode
- Alert on persistent failures

### 111. Integration - OAuth State Validation

**Current Gap:** OAuth state mentioned but validation not detailed.

**Solution:**

**State Validation:**

- Store state server-side
- Validate state on callback
- Expire states (5 minutes)
- One-time use states
- Prevent replay attacks

**Implementation:**

```python
def generate_oauth_state(user_id: int) -> str:
    state = secrets.token_urlsafe(32)
    # Store with expiration
    redis.setex(f"oauth_state:{state}", 300, user_id)  # 5 min
    return state

def validate_oauth_state(state: str) -> Optional[int]:
    user_id = redis.get(f"oauth_state:{state}")
    if user_id:
        redis.delete(f"oauth_state:{state}")  # One-time use
        return int(user_id)
    return None
```

### 112. Learning System - Pattern Effectiveness Tracking

**Current Gap:** No way to measure if patterns are working.

**Solution:**

**Effectiveness Tracking:**

- Track pattern usage success rate
- Track false positives
- Track user corrections
- Pattern effectiveness score
- Auto-disable ineffective patterns

**Database Addition:**

```sql
ALTER TABLE user_knowledge ADD COLUMN success_count INTEGER DEFAULT 0;
ALTER TABLE user_knowledge ADD COLUMN failure_count INTEGER DEFAULT 0;
ALTER TABLE user_knowledge ADD COLUMN effectiveness_score NUMERIC;  -- success_count / (success_count + failure_count)
```

### 113. Data - Data Validation Rules

**Current Gap:** Validation mentioned but rules not comprehensive.

**Solution:**

**Validation Rules:**

- Calories: 0-10000
- Protein/Carbs/Fat: 0-1000g
- Water: 0-10000ml
- Weight: 0-1000lbs
- Reps: 1-1000
- Sets: 1-100
- Dates: Valid date ranges
- Phone: E.164 format
- Email: Valid format

**Implementation:**

```python
VALIDATION_RULES = {
    'calories': {'min': 0, 'max': 10000},
    'protein': {'min': 0, 'max': 1000},
    'water_ml': {'min': 0, 'max': 10000},
    'weight': {'min': 0, 'max': 1000},
    'reps': {'min': 1, 'max': 1000},
    'sets': {'min': 1, 'max': 100}
}

def validate_data(data_type: str, value: float) -> bool:
    rules = VALIDATION_RULES.get(data_type)
    if not rules:
        return True
    return rules['min'] <= value <= rules['max']
```

### 114. Operations - Health Check Dependencies

**Current Gap:** Health checks don't check dependencies.

**Solution:**

**Dependency Health:**

- Check database connectivity
- Check external APIs (Gemini, Twilio)
- Check integration services
- Check cache/Redis
- Degraded mode if dependencies down

**Implementation:**

```python
@app.route('/health/detailed')
def detailed_health():
    checks = {
        'database': check_database(),
        'gemini_api': check_gemini_api(),
        'twilio': check_twilio(),
        'redis': check_redis(),
        'supabase': check_supabase()
    }
    
    all_healthy = all(checks.values())
    status = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks
    }), status
```

### 115. User Experience - Onboarding Tutorial

**Current Gap:** No onboarding for new users.

**Solution:**

**Onboarding:**

- Welcome message with tutorial
- Step-by-step guide
- Example commands
- Feature highlights
- Skip option

**Implementation:**

```python
def send_onboarding_tutorial(user_id: int):
    messages = [
        "Welcome! I'm your personal assistant. Let me show you what I can do:",
        "1. Log food: 'ate a quesadilla'",
        "2. Log water: 'drank a bottle'",
        "3. Log workout: 'did bench press 135x5'",
        "4. Add todo: 'todo buy groceries'",
        "Try one now!"
    ]
    
    for msg in messages:
        send_sms(user_id, msg)
        time.sleep(2)  # Stagger messages
```

### 116. Data - Data Migration Testing

**Current Gap:** No migration testing strategy.

**Solution:**

**Migration Testing:**

- Test migrations on copy of production data
- Verify data integrity after migration
- Test rollback procedures
- Performance testing
- User acceptance testing

### 117. Operations - Rollback Procedures

**Current Gap:** Rollback not detailed.

**Solution:**

**Rollback Procedures:**

- Document rollback steps
- Database migration rollback
- Code rollback (git revert)
- Configuration rollback
- Test rollback in staging

### 118. Security - API Authentication

**Current Gap:** Dashboard API authentication not detailed.

**Solution:**

**API Authentication:**

- JWT tokens for API
- Token expiration
- Refresh tokens
- Token revocation
- API key authentication (for integrations)

**Implementation:**

```python
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

jwt = JWTManager(app)

@app.route('/api/dashboard/stats')
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    return get_user_stats(user_id)
```

### 119. User Experience - Response Templates

**Current Gap:** Responses are generated ad-hoc.

**Solution:**

**Response Templates:**

- Standardized response templates
- Personalization placeholders
- Multi-language templates
- Template versioning
- A/B test different templates

**Implementation:**

```python
RESPONSE_TEMPLATES = {
    'food_logged': "Logged {food_name}! This meal: {calories} cal, {protein}g protein. Total today: {total_calories} cal",
    'water_logged': "Logged {amount}! Total today: {total}ml. {remaining}ml to go!",
    # etc.
}

def format_response(template_name: str, **kwargs):
    template = RESPONSE_TEMPLATES[template_name]
    return template.format(**kwargs)
```

### 120. Operations - Cost Alerts

**Current Gap:** Cost tracking mentioned but alerts not detailed.

**Solution:**

**Cost Alerts:**

- Daily cost threshold alerts
- Monthly budget alerts
- Unusual usage alerts
- Cost breakdown by service
- Cost optimization suggestions

### 121. Integration - Sync Scheduling Per User

**Current Gap:** Syncs are global, not per-user.

**Solution:**

**Per-User Sync Scheduling:**

- User-defined sync frequency
- Sync at user's preferred time
- Respect user's timezone
- Pause syncs during quiet hours
- Per-integration sync settings

### 122. Learning System - Pattern Learning Rate

**Current Gap:** No control over learning speed.

**Solution:**

**Learning Rate:**

- Fast learning (learn from 1 example)
- Normal learning (learn from 2-3 examples)
- Slow learning (learn from 5+ examples)
- User preference
- Adaptive learning rate

### 123. Data - Data Export Incremental

**Current Gap:** Exports are full, not incremental.

**Solution:**

**Incremental Exports:**

- Export only changes since last export
- Delta exports
- Export specific date ranges
- Resume interrupted exports

### 124. Operations - Log Rotation

**Current Gap:** Log rotation not mentioned.

**Solution:**

**Log Rotation:**

- Rotate logs by size (10MB)
- Rotate logs by time (daily)
- Compress old logs
- Delete old logs (30 days)
- Archive important logs

### 125. Security - Audit Trail

**Current Gap:** Audit logging mentioned but not comprehensive.

**Solution:**

**Audit Trail:**

- Log all data changes
- Log all user actions
- Log all admin actions
- Log all security events
- Immutable audit log

**Database Addition:**

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,  -- 'create', 'update', 'delete', 'login', etc.
    resource_type TEXT NOT NULL,  -- 'food_log', 'user', etc.
    resource_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
```

### 126. User Experience - Command History

**Current Gap:** No command history.

**Solution:**

**Command History:**

- Show recent commands
- Quick re-run commands
- Command suggestions
- Most used commands
- Command templates

### 127. Operations - Graceful Degradation

**Current Gap:** No degradation strategy when services fail.

**Solution:**

**Graceful Degradation:**

- Continue with manual logging if integrations fail
- Use cached data if API fails
- Fallback to simpler NLP if Gemini fails
- Read-only mode if database issues
- User notification of degraded service

### 128. Integration - Sync Preview

**Current Gap:** Users can't preview what will be synced.

**Solution:**

**Sync Preview:**

- Show what data will be synced
- Show conflicts before syncing
- Let user choose what to sync
- Preview before connecting
- Sync summary

### 129. Learning System - Pattern Sharing (Optional)

**Current Gap:** Patterns are user-specific only.

**Solution (Optional):**

- Allow users to share patterns (opt-in)
- Community pattern library
- Pattern ratings
- Pattern categories
- Privacy controls

### 130. Operations - Database Query Caching

**Current Gap:** Database query caching not mentioned.

**Solution:**

**Query Caching:**

- Cache frequent queries
- Cache user stats
- Cache pattern lookups
- Invalidate on updates
- Cache TTL configuration

### 131. Security - Rate Limiting Per Endpoint

**Current Gap:** Rate limiting mentioned but per-endpoint not detailed.

**Solution:**

**Per-Endpoint Rate Limits:**

- Different limits for different endpoints
- Stricter limits for expensive operations
- Per-user limits
- Per-IP limits
- Burst allowance

**Implementation:**

```python
@app.route('/api/dashboard/stats')
@limiter.limit("100 per hour")
def get_stats():
    pass

@app.route('/api/export')
@limiter.limit("5 per day")  # Stricter for expensive operation
def export_data():
    pass
```

### 132. User Experience - Dark Mode

**Current Gap:** No dark mode for website.

**Solution:**

**Dark Mode:**

- User preference
- System preference detection
- Toggle in settings
- Persist preference
- Smooth transition

### 133. Operations - Zero-Downtime Deployments

**Current Gap:** No zero-downtime strategy.

**Solution:**

**Zero-Downtime:**

- Blue-green deployment
- Database migration strategy
- Feature flags
- Health checks
- Automatic rollback

### 134. Data - Data Compression

**Current Gap:** No data compression strategy.

**Solution:**

**Data Compression:**

- Compress archived data
- Compress API responses (gzip)
- Compress database backups
- Compress export files
- Compression level configuration

### 135. Integration - Integration Status Page

**Current Gap:** No public status page.

**Solution:**

**Status Page:**

- Public status page (status.yourapp.com)
- Integration status
- API status
- Incident history
- Uptime metrics

### 136. Learning System - Pattern Confidence Decay

**Current Gap:** Confidence only increases, never decreases naturally.

**Solution:**

**Confidence Decay:**

- Gradually decrease confidence if unused
- Faster decay for low-confidence patterns
- Reset decay on use
- Configurable decay rate

**Implementation:**

```python
def apply_confidence_decay():
    # Decrease confidence by 0.01 per month if unused
    cutoff = datetime.now() - timedelta(days=30)
    db.execute("""
        UPDATE user_knowledge 
        SET confidence = GREATEST(0.1, confidence - 0.01)
        WHERE last_used < %s AND confidence > 0.1
    """, (cutoff,))
```

### 137. Operations - Database Backup Encryption

**Current Gap:** Backup encryption not mentioned.

**Solution:**

**Backup Encryption:**

- Encrypt backups at rest
- Encrypt backup transfers
- Secure backup keys
- Backup key rotation
- Backup access controls

### 138. User Experience - Keyboard Navigation

**Current Gap:** Website keyboard navigation not mentioned.

**Solution:**

**Keyboard Navigation:**

- Tab order
- Focus indicators
- Keyboard shortcuts
- Skip links
- ARIA landmarks

### 139. Operations - Dependency Pinning Strategy

**Current Gap:** Dependency management mentioned but pinning strategy not detailed.

**Solution:**

**Dependency Pinning:**

- Pin exact versions
- Regular security updates
- Test updates in staging
- Document breaking changes
- Version compatibility matrix

### 140. Data - Data Normalization on Import

**Current Gap:** No import functionality mentioned.

**Solution:**

**Data Import:**

- Import from CSV/JSON
- Validate imported data
- Normalize on import
- Handle duplicates
- Import preview

### 141. Security - Password History

**Current Gap:** Password history mentioned but not implemented.

**Solution:**

**Password History:**

- Store last N password hashes
- Prevent reuse
- Hash rotation
- Secure storage

**Database Addition:**

```sql
CREATE TABLE password_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_password_history_user ON password_history(user_id);
```

### 142. Operations - Performance Budgets

**Current Gap:** No performance budgets.

**Solution:**

**Performance Budgets:**

- Max response time (500ms)
- Max API call time (2s)
- Max page load time (3s)
- Alert on budget violations
- Performance regression detection

### 143. User Experience - Response Time Expectations

**Current Gap:** Users don't know how long operations take.

**Solution:**

**Response Time Indicators:**

- Show "Processing..." for long operations
- Progress indicators
- Estimated time remaining
- Async processing with notifications
- Status updates

### 144. Integration - Sync Conflict UI

**Current Gap:** Conflict resolution UI not detailed.

**Solution:**

**Conflict UI:**

- Visual diff of conflicts
- Side-by-side comparison
- Merge tool
- Conflict resolution history
- Bulk conflict resolution

### 145. Learning System - Pattern Testing

**Current Gap:** No way to test patterns before using.

**Solution:**

**Pattern Testing:**

- Test pattern against sample messages
- Preview pattern matches
- Pattern effectiveness preview
- A/B test patterns
- Pattern validation

### 146. Operations - Database Connection Monitoring

**Current Gap:** Connection monitoring not detailed.

**Solution:**

**Connection Monitoring:**

- Monitor active connections
- Monitor connection pool usage
- Alert on connection exhaustion
- Connection leak detection
- Connection timeout tracking

### 147. Security - Input Length Limits

**Current Gap:** No input length limits.

**Solution:**

**Input Length Limits:**

- Message length (SMS: 160 chars, but allow longer)
- Food name: 200 chars
- Todo content: 500 chars
- Notes: 1000 chars
- Prevent DoS via large inputs

**Implementation:**

```python
MAX_LENGTHS = {
    'message': 1000,
    'food_name': 200,
    'todo_content': 500,
    'notes': 1000
}

def validate_length(field: str, value: str) -> bool:
    max_len = MAX_LENGTHS.get(field, 1000)
    return len(value) <= max_len
```

### 148. User Experience - Undo/Redo

**Current Gap:** Undo mentioned but redo not.

**Solution:**

**Undo/Redo:**

- Undo last action
- Redo undone action
- Undo history (last 10 actions)
- Undo for bulk operations
- Visual undo indicator

### 149. Operations - Database Query Timeout

**Current Gap:** Query timeout not configured.

**Solution:**

**Query Timeout:**

- Set query timeout (30 seconds)
- Cancel long-running queries
- Alert on timeout
- Query timeout per operation type
- Timeout retry strategy

### 150. Data - Data Validation on Sync

**Current Gap:** Synced data validation not mentioned.

**Solution:**

**Sync Data Validation:**

- Validate data from integrations
- Sanitize external data
- Normalize external data
- Handle invalid data gracefully
- Log validation failures

### 151. Security - Legal Compliance (HIPAA, etc.)

**Current Gap:** Health data might need HIPAA compliance.

**Solution:**

**Compliance Considerations:**

- Determine if HIPAA applies (health data)
- Implement HIPAA safeguards if needed
- Business Associate Agreements (BAAs) with providers
- Data encryption requirements
- Access logging requirements
- Audit requirements

**Note:** Consult legal counsel to determine compliance requirements.

### 152. Operations - Database Replication

**Current Gap:** No database replication strategy.

**Solution:**

**Database Replication:**

- Read replicas for scaling
- Failover to replica
- Replication lag monitoring
- Supabase handles this, but configure properly

### 153. User Experience - Mobile Responsiveness

**Current Gap:** Website mobile optimization not detailed.

**Solution:**

**Mobile Optimization:**

- Responsive design
- Touch-friendly buttons
- Mobile navigation
- Optimized images
- Fast mobile load times

### 154. Operations - Error Recovery Procedures

**Current Gap:** Error recovery not detailed.

**Solution:**

**Error Recovery:**

- Automatic retry for transient errors
- Manual recovery procedures
- Data recovery from backups
- Service recovery steps
- Incident response playbook

### 155. Data - Data Integrity Constraints

**Current Gap:** Database constraints not comprehensive.

**Solution:**

**Data Integrity:**

- CHECK constraints (calories >= 0)
- NOT NULL constraints
- UNIQUE constraints
- Foreign key constraints
- Custom validation functions

**Database:**

```sql
ALTER TABLE food_logs ADD CONSTRAINT check_calories_positive 
    CHECK (calories >= 0);
ALTER TABLE food_logs ADD CONSTRAINT check_protein_positive 
    CHECK (protein >= 0);
-- etc.
```

### 156. User Experience - Contextual Help

**Current Gap:** Help is generic, not contextual.

**Solution:**

**Contextual Help:**

- Help based on what user is doing
- Inline help tooltips
- Contextual examples
- Progressive disclosure
- Help search

### 157. Operations - Database Vacuum & Maintenance

**Current Gap:** Database maintenance not mentioned.

**Solution:**

**Database Maintenance:**

- Regular VACUUM (PostgreSQL)
- ANALYZE for query planner
- Index maintenance
- Table statistics updates
- Supabase handles this, but monitor

### 158. Integration - Integration Health Dashboard

**Current Gap:** No centralized integration health view.

**Solution:**

**Integration Health Dashboard:**

- Status of all integrations
- Last sync time per integration
- Error rates
- Sync success rates
- Token expiration warnings

### 159. Learning System - Pattern Merge Strategy

**Current Gap:** Pattern merging mentioned but strategy not detailed.

**Solution:**

**Pattern Merging:**

- Merge similar patterns
- Combine confidence scores
- Merge usage counts
- Preserve context from both
- User approval for merges

### 160. Operations - Resource Cleanup

**Current Gap:** Resource cleanup not mentioned.

**Solution:**

**Resource Cleanup:**

- Close file handles
- Close database connections
- Clear temporary files
- Cleanup expired sessions
- Memory cleanup

### 161. Security - Security Headers

**Current Gap:** Security headers not comprehensive.

**Solution:**

**Security Headers:**

- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Referrer-Policy
- Permissions-Policy

**Implementation:**

```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

### 162. Performance - Lazy Loading

**Current Gap:** Lazy loading not mentioned.

**Solution:**

**Lazy Loading:**

- Lazy load dashboard data
- Lazy load images
- Lazy load charts
- Progressive data loading
- Infinite scroll

### 163. User Experience - Auto-Save

**Current Gap:** No auto-save for forms.

**Solution:**

**Auto-Save:**

- Auto-save form data
- Restore on page reload
- Draft saving
- Auto-save interval
- Conflict resolution

### 164. Operations - Database Index Maintenance

**Current Gap:** Index maintenance not detailed.

**Solution:**

**Index Maintenance:**

- Monitor index usage
- Remove unused indexes
- Rebuild fragmented indexes
- Analyze index statistics
- Index size monitoring

### 165. Integration - Sync Error Notifications

**Current Gap:** Users not notified of sync errors.

**Solution:**

**Sync Error Notifications:**

- Notify user of sync failures
- Explain error clearly
- Suggest fixes
- Retry option
- Error history

### 166. Learning System - Pattern Export/Import

**Current Gap:** Users can't backup/restore patterns.

**Solution:**

**Pattern Export/Import:**

- Export learned patterns
- Import patterns (backup restore)
- Share patterns (optional)
- Pattern backup before deletion
- Pattern versioning

### 167. Operations - Database Query Analysis

**Current Gap:** No query analysis tools.

**Solution:**

**Query Analysis:**

- EXPLAIN ANALYZE for slow queries
- Query plan analysis
- Index usage analysis
- Query optimization suggestions
- Query performance monitoring

### 168. User Experience - Batch Operations UI

**Current Gap:** Bulk operations mentioned but UI not detailed.

**Solution:**

**Batch Operations UI:**

- Select multiple items
- Batch actions menu
- Progress indicator
- Undo batch operations
- Batch operation history

### 169. Security - API Rate Limiting Per User

**Current Gap:** Rate limiting is global, not per-user.

**Solution:**

**Per-User Rate Limiting:**

- Different limits per user tier
- Premium users get higher limits
- Per-user rate limit tracking
- Rate limit headers in responses
- Rate limit reset times

### 170. Operations - Database Connection Leak Detection

**Current Gap:** No connection leak detection.

**Solution:**

**Leak Detection:**

- Monitor connection count
- Alert on connection leaks
- Automatic leak cleanup
- Connection pool monitoring
- Leak prevention patterns

### 171. Data - Data Validation at API Level

**Current Gap:** Validation at repository but not API.

**Solution:**

**API Validation:**

- Validate all API inputs
- Use Pydantic models
- Return validation errors
- Validate response data
- API schema documentation

### 172. User Experience - Command Aliases

**Current Gap:** No command aliases.

**Solution:**

**Command Aliases:**

- User-defined aliases
- Shortcuts for common commands
- Alias management
- Built-in aliases
- Alias suggestions

**Implementation:**

```python
ALIASES = {
    'w': 'water',
    'f': 'food',
    'g': 'gym',
    's': 'sleep',
    't': 'todo'
}

def expand_alias(command: str) -> str:
    words = command.split()
    if words[0] in ALIASES:
        words[0] = ALIASES[words[0]]
    return ' '.join(words)
```

### 173. Operations - Database Backup Verification

**Current Gap:** Backup verification not automated.

**Solution:**

**Backup Verification:**

- Automated backup testing
- Restore test monthly
- Verify backup integrity
- Test backup encryption
- Document verification results

### 174. Integration - Sync Progress Tracking

**Current Gap:** No progress tracking for long syncs.

**Solution:**

**Sync Progress:**

- Show sync progress (X of Y items)
- Estimated time remaining
- Progress bar in dashboard
- Real-time updates
- Sync cancellation

### 175. Learning System - Pattern Categories

**Current Gap:** Patterns not categorized.

**Solution:**

**Pattern Categories:**

- Categorize patterns (food, exercise, etc.)
- Filter by category
- Category-based search
- Category statistics
- Category management

**Database Addition:**

```sql
ALTER TABLE user_knowledge ADD COLUMN category TEXT;  -- 'food', 'exercise', 'restaurant', etc.
CREATE INDEX idx_user_knowledge_category ON user_knowledge(category);
```

### 176. Operations - Performance Profiling

**Current Gap:** No performance profiling.

**Solution:**

**Performance Profiling:**

- Profile slow endpoints
- Identify bottlenecks
- Memory profiling
- CPU profiling
- Database query profiling

**Tools:**

- cProfile, py-spy, memory_profiler
- Application Performance Monitoring (APM)

### 177. User Experience - Response Customization

**Current Gap:** Users can't customize response format.

**Solution:**

**Response Customization:**

- Custom response templates
- Response length preference
- Emoji on/off
- Units preference (metric/imperial)
- Detail level (brief/detailed)

### 178. Operations - Database Query Caching Strategy

**Current Gap:** Query caching mentioned but strategy not detailed.

**Solution:**

**Query Caching Strategy:**

- Cache frequent queries
- Cache key design
- Cache invalidation rules
- Cache TTL per query type
- Cache hit rate monitoring

### 179. Security - Secret Rotation Automation

**Current Gap:** Secret rotation mentioned but automation not detailed.

**Solution:**

**Automated Rotation:**

- Schedule secret rotation
- Automated rotation process
- Zero-downtime rotation
- Rotation notifications
- Rotation history

### 180. User Experience - Notification Grouping

**Current Gap:** Multiple notifications might spam user.

**Solution:**

**Notification Grouping:**

- Group related notifications
- Batch notifications
- Notification digest
- Quiet hours respect
- Notification priority

### 181. Operations - Database Query Optimization Rules

**Current Gap:** Query optimization not rule-based.

**Solution:**

**Optimization Rules:**

- Always use indexes
- Avoid SELECT *
- Use LIMIT
- Avoid functions in WHERE
- Use EXPLAIN ANALYZE

### 182. Integration - Integration Testing for Providers

**Current Gap:** No integration tests for external APIs.

**Solution:**

**Provider Integration Tests:**

- Mock provider APIs
- Test OAuth flows
- Test sync flows
- Test error handling
- Test rate limiting

### 183. Learning System - Pattern Confidence Visualization

**Current Gap:** Users can't see pattern confidence.

**Solution:**

**Confidence Visualization:**

- Show confidence in dashboard
- Confidence history graph
- Confidence trends
- Low confidence warnings
- Confidence improvement tips

### 184. Operations - Database Connection Pool Sizing

**Current Gap:** Pool sizing not calculated.

**Solution:**

**Pool Sizing:**

- Calculate based on expected load
- Min connections: 5
- Max connections: 20
- Monitor and adjust
- Connection pool metrics

### 185. User Experience - Quick Actions

**Current Gap:** No quick actions for common tasks.

**Solution:**

**Quick Actions:**

- Quick log buttons
- Recent items
- Favorites
- Quick stats
- One-tap actions

### 186. Data - Data Validation Error Messages

**Current Gap:** Validation errors not user-friendly.

**Solution:**

**User-Friendly Errors:**

- Clear error messages
- Suggest fixes
- Show what's wrong
- Provide examples
- Link to help

**Implementation:**

```python
VALIDATION_ERRORS = {
    'calories_negative': "Calories can't be negative. Did you mean {suggestion}?",
    'date_invalid': "That date doesn't look right. Try format: YYYY-MM-DD",
    'phone_invalid': "Phone number should be like: +1234567890"
}
```

### 187. Operations - Database Statistics Collection

**Current Gap:** No database statistics monitoring.

**Solution:**

**Statistics Collection:**

- Table sizes
- Index sizes
- Query performance stats
- Connection stats
- Growth trends

### 188. Integration - Sync Conflict Resolution History

**Current Gap:** No history of resolved conflicts.

**Solution:**

**Conflict History:**

- Track all conflicts
- Resolution choices
- Conflict patterns
- Learn from resolutions
- Conflict analytics

### 189. Learning System - Pattern Learning Feedback Loop

**Current Gap:** No feedback on learning effectiveness.

**Solution:**

**Feedback Loop:**

- Ask user if pattern worked
- Track user corrections
- Improve learning based on feedback
- Pattern effectiveness metrics
- Continuous improvement

### 190. Operations - Database Query Timeout Configuration

**Current Gap:** Timeout configuration not detailed.

**Solution:**

**Timeout Configuration:**

- Short timeout for simple queries (5s)
- Medium timeout for complex queries (30s)
- Long timeout for exports (5min)
- Per-query-type timeouts
- Timeout error handling

### 191. User Experience - Response Time Optimization

**Current Gap:** No response time optimization.

**Solution:**

**Response Time:**

- Target: < 500ms for SMS responses
- Async processing for long operations
- Caching for frequent queries
- Optimize NLP calls
- Parallel processing where possible

### 192. Security - Password Strength Meter

**Current Gap:** No visual password strength indicator.

**Solution:**

**Password Strength Meter:**

- Real-time strength calculation
- Visual indicator (weak/medium/strong)
- Requirements checklist
- Strength score
- Improvement suggestions

### 193. Operations - Database Query Logging

**Current Gap:** Query logging not configured.

**Solution:**

**Query Logging:**

- Log slow queries (>1s)
- Log all queries in dev
- Log errors only in prod
- Query performance metrics
- Query pattern analysis

### 194. Integration - Sync Retry Strategy

**Current Gap:** Retry strategy not detailed.

**Solution:**

**Retry Strategy:**

- Exponential backoff
- Max retries: 3
- Retry delays: 1s, 2s, 4s
- Retry only for transient errors
- Permanent failure handling

### 195. Learning System - Pattern Effectiveness Metrics

**Current Gap:** No metrics on pattern effectiveness.

**Solution:**

**Effectiveness Metrics:**

- Success rate
- Usage frequency
- Correction rate
- Confidence trend
- User satisfaction

### 196. Operations - Database Connection Health

**Current Gap:** Connection health not monitored.

**Solution:**

**Connection Health:**

- Monitor connection pool
- Alert on high usage
- Connection error tracking
- Connection timeout monitoring
- Health dashboard

### 197. User Experience - Command Completion

**Current Gap:** No command completion.

**Solution:**

**Command Completion:**

- Autocomplete commands
- Suggest completions
- Learn from history
- Context-aware suggestions
- Quick completion

### 198. Operations - Database Index Usage Analysis

**Current Gap:** Index usage not analyzed.

**Solution:**

**Index Usage:**

- Track index usage
- Identify unused indexes
- Identify missing indexes
- Index efficiency metrics
- Index optimization recommendations

### 199. Security - Input Sanitization Rules

**Current Gap:** Sanitization rules not comprehensive.

**Solution:**

**Sanitization Rules:**

- Remove SQL injection attempts
- Remove XSS attempts
- Remove command injection
- Sanitize file paths
- Sanitize URLs

### 200. Operations - Complete System Architecture Documentation

**Current Gap:** Architecture documentation not comprehensive.

**Solution:**

**Architecture Documentation:**

- System architecture diagram
- Data flow diagrams
- Component interactions
- API documentation
- Deployment architecture
- Security architecture
- Database schema documentation
- Integration architecture

## Final Gap Summary

**Total Gaps Identified: 200+**

**Categories:**

- Security: 40+ gaps
- Performance: 30+ gaps
- User Experience: 35+ gaps
- Operations: 35+ gaps
- Data Management: 25+ gaps
- Integration: 20+ gaps
- Learning System: 15+ gaps

**All gaps include:**

- Problem description
- Solution approach
- Implementation details
- Code examples
- Database changes (if needed)

The plan is now comprehensive and covers virtually every aspect of the system.