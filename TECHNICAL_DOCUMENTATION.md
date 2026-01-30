# SMS Assistant - Technical Documentation

## Project Overview

SMS Assistant is a production-grade, multi-user personal productivity chatbot that operates entirely through SMS messaging and a web dashboard. The system combines advanced natural language processing, adaptive machine learning, and seamless third-party integrations to create an intelligent assistant that learns user-specific patterns and preferences over time.

The architecture is built on a modular, scalable foundation using Python, Flask, Supabase (PostgreSQL), and Google's Gemini API, with a clear separation of concerns across NLP processing, business logic, data persistence, and background job orchestration.

---

## Core Architecture

### Modular Design Philosophy

The system is organized into distinct, independently testable modules:

- **`core/`** - Message processing engine, conversation context management, session handling
- **`nlp/`** - Natural language processing components (intent classification, entity extraction, domain-specific parsing)
- **`handlers/`** - Intent-specific business logic handlers (food, water, gym, todos, queries)
- **`data/`** - Repository pattern for database interactions (9 entity-specific repositories)
- **`learning/`** - Adaptive learning system (pattern extraction, association learning, context analysis)
- **`services/`** - Background job services (scheduler, reminders, notifications, syncs)
- **`web/`** - Web dashboard and authentication system
- **`integrations/`** - Third-party integration framework (Fitbit, Google Calendar)
- **`responses/`** - Response formatting and SMS message construction

This modular structure enables independent development, testing, and maintenance of each component while maintaining clear interfaces between modules.

---

## Natural Language Processing System

### Intent Classification

The system uses Google's Gemini API (configurable models: Gemini 3 Flash Preview, Gemini 2.5 Flash, Gemma-3-12b-it) to classify user messages into 20+ distinct intents:

- **Logging Intents**: `water_logging`, `food_logging`, `gym_workout`, `sleep_logging`
- **Task Management**: `todo_add`, `reminder_set`, `assignment_add`, `task_complete`
- **Query Intents**: `stats_query`, `what_should_i_do`, `food_suggestion`
- **Learning Intents**: `fact_storage`, `fact_query`
- **System Intents**: `undo_edit`, `vague_completion`, `integration_manage`

The `IntentClassifier` uses few-shot prompting with examples to achieve high accuracy across diverse phrasings and user communication styles.

### Entity Extraction

The `EntityExtractor` identifies structured data from unstructured text:
- **Temporal entities**: Dates, times, relative time expressions ("tomorrow", "in 2 hours")
- **Quantities**: Water amounts (ml, oz, bottles), weights (lbs, kg), repetitions, sets
- **Food items**: Restaurant names, menu items, portion sizes
- **Exercise data**: Exercise names, weights, reps, sets, muscle groups
- **Task metadata**: Due dates, priorities, assignment classes

### Domain-Specific Parsing

The `Parser` module contains specialized parsing logic for each domain:

**Food Parsing:**
- Restaurant name extraction from custom JSON database (20+ restaurants)
- Menu item matching with fuzzy matching and synonym handling
- Automatic macro calculation (calories, protein, carbs, fat) from restaurant-specific data
- Portion multiplier detection ("double", "half", "2x")

**Nutrition Resolver (Milestone A):**
- When the local restaurant JSON database does not match and the user didn’t explicitly provide macros, Alfred falls back to a tiered nutrition resolver.
- Sources (in order): **USDA FoodData Central** → **Open Food Facts** → **Nutritionix** (if configured). If a restaurant is provided, Nutritionix is tried first.
- Results are cached in Supabase to reduce repeated external API calls.

Key code:
- Resolver: `services/nutrition/resolver.py`
- Providers: `services/nutrition/providers.py`
- Cache repo: `data/nutrition_cache_repository.py`
- Food log metadata repo: `data/food_log_metadata_repository.py`

Schema additions:
- `nutrition_cache` and `food_log_metadata` tables are defined in `supabase_schema_nutrition_pipeline.sql`.

**Dashboard image uploads (Milestone B):**
- Dashboard can upload images (nutrition labels / receipts / food photos) via `POST /dashboard/api/upload/image` (multipart form-data).
- Images are stored in **Supabase Storage** (bucket configurable via `FOOD_IMAGE_BUCKET`).
- Upload metadata is stored in `food_image_uploads` for later processing (Milestone C).

Key code:
- Route: `web/routes.py`
- Repo: `data/food_image_upload_repository.py`

Schema additions:
- `food_image_uploads` table is defined in `supabase_schema_nutrition_pipeline.sql`.

**Guardrails (Milestone D):**
- Rate limiting via Flask-Limiter is enabled in `app.py` and applied to upload/process/delete endpoints.\n+- Receipt processing skips creating “0 calorie” logs when nutrition can’t be resolved; unresolved items are returned for follow-up.\n+- A deletion endpoint exists for privacy cleanup: `POST /dashboard/api/upload/image/delete`.

**Water Parsing:**
- Multi-unit support (ml, oz, liters, bottles with configurable bottle size)
- Implicit quantity inference ("drank a bottle" → 710ml default)
- Cumulative tracking with daily goal progress

**Gym Parsing:**
- Exercise name extraction from workout database
- Set/rep/weight parsing from various formats ("135x5", "3 sets of 5 at 225")
- Muscle group inference from exercise names
- Notes and additional context capture

**Temporal Parsing:**
- Relative time expressions ("in 30 minutes", "tomorrow at 3pm")
- Absolute datetime parsing
- Timezone-aware date handling (UTC storage, user timezone display)

### Pattern Matching Integration

Before NLP classification, the system applies learned user-specific patterns via `PatternMatcher`. This allows the system to recognize user-specific terminology (e.g., "dhamaka" = workout) without requiring explicit NLP classification, improving both accuracy and response time.

---

## Adaptive Learning System

### Pattern Extraction

The `PatternExtractor` identifies four types of learning opportunities from user messages:

1. **Explicit Teaching**: "X, count it as Y" (e.g., "dhamaka, count it as workout")
2. **Correction Patterns**: User correcting system mistakes
3. **Confirmation Patterns**: User confirming system interpretations
4. **Context-Based Associations**: Inferring relationships from conversation context

Patterns are extracted using regex-based rules combined with NLP entity extraction to identify the significant terms (filtering out stop words, pronouns, and common verbs).

### Association Learning

The `AssociationLearner` manages pattern associations with confidence scores:
- **Confidence Scoring**: Patterns start at 0.5 confidence, increase with successful usage
- **Reinforcement**: Each successful pattern application increases confidence
- **Decay**: Unused patterns gradually decrease in confidence
- **User-Specific Storage**: All patterns stored per-user in `user_knowledge` table

Patterns are stored with metadata:
- Pattern term (e.g., "dhamaka")
- Associated intent (e.g., "gym_workout")
- Associated entities (e.g., exercise name)
- Confidence score (0.0 - 1.0)
- Usage count and last used timestamp

### Context Analysis

The `ContextAnalyzer` detects learning opportunities by:
- Identifying explicit teaching keywords ("count it as", "log it as", "that's a")
- Detecting correction patterns ("no, that's actually...")
- Recognizing confirmation responses ("yes", "correct", "that's right")
- Analyzing conversation flow for implicit learning opportunities

### Learning Orchestration

The `LearningOrchestrator` coordinates the entire learning pipeline:
1. **Pre-Processing**: Applies learned patterns before NLP classification
2. **Post-Processing**: Extracts new patterns from user messages
3. **Pattern Storage**: Persists patterns to `KnowledgeRepository`
4. **Confidence Management**: Updates confidence scores based on usage

This creates a feedback loop where the system becomes more accurate and personalized over time without requiring retraining or manual updates.

---

## Data Layer Architecture

### Repository Pattern

All database interactions use a repository pattern with a `BaseRepository` providing common CRUD operations:

- **Generic Methods**: `create()`, `get_by_id()`, `update()`, `delete()`, `filter()`, `get_all()`
- **Type Safety**: Type hints throughout for better IDE support and error detection
- **Error Handling**: Consistent error handling with Supabase API error translation
- **Query Building**: Fluent query builder interface for complex filters

### Entity-Specific Repositories

Nine specialized repositories extend `BaseRepository`:

1. **UserRepository**: User account management, phone/email lookup, authentication
2. **FoodRepository**: Food log CRUD, date-based queries, macro aggregation
3. **WaterRepository**: Water log management, daily totals, goal tracking
4. **GymRepository**: Workout logs, exercise-based queries, date filtering
5. **TodoRepository**: Todos and reminders, due date queries, completion tracking
6. **SleepRepository**: Sleep log management, duration calculations
7. **AssignmentRepository**: Academic assignments with class tracking
8. **KnowledgeRepository**: User-specific learned patterns and associations
9. **IntegrationRepository**: Third-party connection management, sync history

Each repository provides domain-specific methods while inheriting common functionality from `BaseRepository`.

### Database Schema

The PostgreSQL schema (Supabase) includes:

- **19 Tables**: Users, food_logs, water_logs, gym_logs, todos, reminders, sleep_logs, assignments, user_knowledge, integration_connections, sync_history, and more
- **Row-Level Security (RLS)**: All tables have RLS policies ensuring users can only access their own data
- **Foreign Keys**: Proper referential integrity with `ON DELETE CASCADE` where appropriate
- **Indexes**: Optimized indexes on frequently queried columns (user_id, timestamps, phone_number, email)
- **Composite Keys**: Proper composite primary keys for junction tables
- **Timezone Handling**: UTC storage with timezone-aware queries

### Data Consistency

- **Transaction Support**: Critical operations use database transactions
- **Constraint Validation**: Database-level constraints prevent invalid data
- **Soft Deletes**: Optional soft delete pattern for audit trails
- **Timestamp Management**: Automatic `created_at` and `updated_at` tracking

---

## Message Processing Engine

### MessageProcessor

The `MessageProcessor` is the central orchestration component that:

1. **User Resolution**: Maps phone numbers to user IDs (creates users if needed)
2. **Session Management**: Maintains conversation state and context
3. **Pattern Application**: Applies learned patterns before NLP
4. **Intent Classification**: Routes to appropriate handler
5. **Entity Extraction**: Extracts structured data from messages
6. **Handler Execution**: Delegates to intent-specific handlers
7. **Response Formatting**: Formats responses for SMS (character limits, formatting)
8. **Learning Processing**: Extracts and stores new patterns after handling

### Conversation Context

The `ConversationContext` class provides rich context for handlers:

- **Today's Summary**: Aggregated stats for current day (water, food, gym, todos)
- **Recent Activity**: Last N entries for each log type
- **Upcoming Items**: Todos, reminders, assignments due soon
- **Historical Patterns**: User's typical behavior for context-aware suggestions

Context is cached per user to reduce database queries and improve response time.

### Session Management

The `SessionManager` handles conversation state:

- **Pending Confirmations**: Stores pending confirmation requests (e.g., "Did you mean X?")
- **Multi-Turn Conversations**: Maintains context across multiple messages
- **Selection Tracking**: Tracks numbered option selections ("what just happened" mode)
- **Timeout Handling**: Automatically clears stale session data

---

## Intent Handlers

Each intent has a dedicated handler class extending `BaseHandler`:

### FoodHandler
- Parses food items from restaurant database
- Calculates macros from restaurant-specific data
- Handles portion multipliers
- Stores food logs with full nutritional information

### WaterHandler
- Parses water amounts in multiple units
- Tracks daily totals against goals
- Provides progress feedback ("X bottles to reach goal")
- Handles goal setting and updates

### GymHandler
- Extracts exercise, sets, reps, weight
- Matches exercises to workout database
- Infers muscle groups
- Stores workout logs with structured data

### TodoHandler
- Creates todos and reminders
- Parses due dates and times
- Handles task completion ("called mom" → matches and completes todo)
- Manages reminder scheduling

### QueryHandler
- Aggregates stats across multiple data types
- Provides date-based queries ("what did I eat yesterday")
- Generates context-aware suggestions ("what should I do now")
- Handles complex multi-table queries

### IntegrationHandler
- Manages third-party integration commands via SMS
- Provides connection links
- Triggers manual syncs
- Lists connected integrations

All handlers follow a consistent interface:
- `handle()` method takes message, entities, and user context
- Returns formatted response string
- Handles errors gracefully with user-friendly messages

---

## Background Job System

### Job Scheduler

The `JobScheduler` uses APScheduler (Advanced Python Scheduler) to manage all background tasks:

- **Thread Pool Executor**: 5 worker threads for concurrent job execution
- **Job Coalescing**: Multiple pending executions combined into one
- **Misfire Handling**: 5-minute grace period for missed jobs
- **Timezone Support**: All jobs run in UTC with proper timezone conversion
- **Job Management**: Add, remove, and query scheduled jobs programmatically

### Reminder Service

The `ReminderService` handles:

**Reminder Follow-ups:**
- Checks reminders sent but not completed
- Sends follow-up after configurable delay (default: 30 minutes)
- Suggests rescheduling for overdue reminders
- Provides quick reschedule options (later today, tomorrow morning)

**Task Decay:**
- Identifies stale todos (default: 7+ days old)
- Sends decay check messages asking if task is still relevant
- Provides options: keep, reschedule, delete
- Prevents silent task list clutter

### Notification Service

The `NotificationService` provides:

**Gentle Nudges:**
- **Water Nudges**: Detects if user is behind expected water intake pace
- **Gym Nudges**: Reminds if no workout in 2+ days
- Context-aware messaging (references personal patterns, not absolute goals)
- Non-judgmental, informative tone

**Weekly Digest:**
- Calculates weekly averages (water, calories, gym frequency)
- Computes task completion rates
- Sends concise, skimmable summary
- Scheduled for Monday at configured hour (default: 8 PM)

### Sync Service

The `SyncService` manages periodic integration synchronization:

- Syncs all active integrations every 4 hours
- Handles token refresh automatically
- Deduplicates synced data
- Logs sync history for debugging
- Maps external data to internal schema

---

## Web Dashboard & Authentication

### Authentication System

The `AuthManager` provides:

- **User Registration**: Email/password with optional phone number
- **Login**: Session-based authentication with bcrypt password hashing
- **Password Reset**: Token-based reset flow (email delivery)
- **Phone Verification**: SMS code verification for phone numbers
- **Session Management**: Secure session handling with Flask sessions
- **Account Security**: Failed login attempt tracking, account locking

### Dashboard Data Layer

The `DashboardData` class provides:

- **Date Stats**: Aggregated statistics for any date (food, water, gym, todos, reminders, assignments)
- **Trends**: Multi-day trend analysis (7, 30, 90 days)
- **Calendar Data**: Month-view data with activity indicators
- **Frontend Formatting**: Data formatted specifically for JavaScript frontend consumption

### Web Routes

The dashboard includes:

- **Main Dashboard**: Calendar view with date-based stats
- **Chat Interface**: Web-based chat for testing (uses same MessageProcessor as SMS)
- **Settings Page**: Account management, password changes, phone verification
- **Integrations Page**: Connect/disconnect third-party services
- **Test Jobs Page**: Manual background job triggering for testing

All routes are protected with `@require_login` decorator ensuring authenticated access.

---

## Third-Party Integrations

### Integration Framework

The system uses a plugin-based architecture for integrations:

**BaseIntegration Interface:**
- `get_authorization_url()` - OAuth initiation
- `exchange_code_for_tokens()` - Token exchange
- `refresh_access_token()` - Token refresh
- `sync_data()` - Data synchronization
- `map_external_to_internal()` - Data transformation
- `revoke_token()` - Disconnection

### Integration Auth Manager

The `IntegrationAuthManager` handles:

- **OAuth Flows**: Complete OAuth 2.0 flows for all providers
- **Token Encryption**: Fernet encryption for stored tokens
- **CSRF Protection**: State token generation and validation
- **Token Refresh**: Automatic refresh before expiration
- **Error Handling**: Graceful handling of expired/invalid tokens

### Sync Manager

The `SyncManager` orchestrates:

- **Data Fetching**: Retrieves data from external APIs
- **Deduplication**: Prevents duplicate log entries
- **Data Mapping**: Transforms external schema to internal format
- **Sync Logging**: Tracks all sync operations with timestamps and results
- **Error Recovery**: Handles API failures gracefully

### Implemented Integrations

**Fitbit Integration:**
- OAuth 2.0 authentication
- Workout data sync (activities, exercises, duration)
- Sleep data sync (duration, quality metrics)
- Webhook support for real-time updates
- Last 30 days of data synced on connection

**Google Calendar Integration:**
- OAuth 2.0 authentication
- Event fetching for context (upcoming events)
- Calendar events used for "what should I do now" suggestions
- Timezone-aware event handling

**Google Fit Integration:**
- Structure created, implementation deferred
- Ready for future expansion

### Webhook Handlers

The `WebhookHandler` processes real-time updates:

- **Fitbit Webhooks**: Verifies webhook signatures, processes activity/sleep updates
- **Google Webhooks**: Placeholder for Pub/Sub webhook processing
- **Automatic Sync**: Triggers sync on webhook receipt

---

## Response Formatting

The `ResponseFormatter` ensures SMS-friendly output:

- **Character Limits**: Truncates long responses (1500 character limit)
- **Line Breaks**: Preserves formatting for readability
- **Emoji Support**: Optional emoji for visual clarity
- **List Formatting**: Numbered lists for options
- **Progress Indicators**: Visual progress bars for goals (in dashboard)

---

## Security Features

### Authentication Security

- **Password Hashing**: bcrypt with configurable rounds
- **Session Security**: Flask secret key for session encryption
- **CSRF Protection**: State tokens for OAuth flows
- **Account Locking**: Automatic lockout after 5 failed login attempts
- **Token Encryption**: Fernet encryption for OAuth tokens

### Data Security

- **Row-Level Security**: Database-level access control (RLS policies)
- **Input Validation**: Server-side validation for all inputs
- **SQL Injection Prevention**: Parameterized queries via Supabase client
- **XSS Prevention**: Template escaping in Jinja2 templates

### API Security

- **Webhook Verification**: Signature verification for Fitbit webhooks
- **Rate Limiting**: Ready for rate limiting implementation
- **Error Message Sanitization**: No sensitive data in error messages

---

## Configuration Management

The `Config` class centralizes all configuration:

- **Environment Variables**: All sensitive data via `.env` file
- **Feature Flags**: Enable/disable features (weekly digest, gentle nudges, task decay)
- **Timing Configuration**: Configurable intervals for all scheduled jobs
- **Model Selection**: Configurable Gemini model per environment
- **Database Configuration**: Supabase connection details
- **Integration Credentials**: OAuth client IDs and secrets

Configuration is validated on startup to ensure required values are present.

---

## Error Handling & Logging

### Error Handling Strategy

- **Graceful Degradation**: System continues operating even if non-critical components fail
- **User-Friendly Messages**: Errors translated to user-friendly language
- **Error Logging**: All errors logged with full context
- **Fallback Responses**: Default responses when NLP fails

### Logging

- **Structured Logging**: JSON-formatted logs for parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context Preservation**: User ID, phone number, message included in logs
- **Performance Logging**: Timing information for optimization

---

## Testing Infrastructure

### Test Coverage

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end message processing tests
- **Repository Tests**: Database interaction verification
- **NLP Tests**: Intent classification and entity extraction accuracy

### Testing Tools

- **Chat Interface**: Web-based testing without SMS
- **Manual Job Triggers**: Test background jobs on-demand
- **Health Endpoints**: `/health`, `/health/ready`, `/health/live` for monitoring

---

## Performance Optimizations

### Caching Strategy

- **Context Caching**: Conversation context cached per user
- **Database Query Optimization**: Indexed queries, efficient filters
- **Session Caching**: In-memory session storage
- **Pattern Caching**: Learned patterns loaded once per user session

### Database Optimization

- **Indexes**: Strategic indexes on frequently queried columns
- **Query Optimization**: Efficient date range queries
- **Connection Pooling**: Supabase client connection management
- **Batch Operations**: Bulk inserts where possible

### Response Time

- **Async Processing**: Background jobs don't block message processing
- **Parallel Queries**: Multiple repository queries can run concurrently
- **Lazy Loading**: Data loaded only when needed

---

## Scalability Considerations

### Multi-User Architecture

- **User Isolation**: Complete data separation via RLS policies
- **Scalable Repositories**: Repository pattern supports horizontal scaling
- **Stateless Processing**: Message processing is stateless (except sessions)
- **Background Jobs**: Jobs scale with user count automatically

### Database Scalability

- **Supabase**: Managed PostgreSQL with automatic scaling
- **Efficient Queries**: Optimized for large datasets
- **Partitioning Ready**: Schema supports future partitioning if needed

### API Scalability

- **Rate Limiting Ready**: Infrastructure for rate limiting
- **Caching Layer**: Ready for Redis integration
- **Load Balancing**: Stateless design supports load balancing

---

## Deployment Architecture

### Application Structure

- **Single Entry Point**: `app.py` as main Flask application
- **Modular Imports**: Clean import structure for deployment
- **Environment Configuration**: All config via environment variables
- **Health Checks**: Kubernetes-ready health endpoints

### Background Jobs

- **Persistent Scheduler**: APScheduler persists job state
- **Graceful Shutdown**: Jobs complete before shutdown
- **Job Recovery**: Missed jobs handled with grace period

---

## Key Technical Achievements

1. **Adaptive Learning**: System learns user-specific patterns without retraining
2. **Multi-Modal Input**: Handles both SMS and web chat with same processing engine
3. **Rich Context Awareness**: Synthesizes multiple data sources for intelligent suggestions
4. **Production-Ready**: Error handling, logging, security, scalability considerations
5. **Extensible Architecture**: Easy to add new intents, handlers, integrations
6. **Type Safety**: Comprehensive type hints for better maintainability
7. **Clean Architecture**: Clear separation of concerns, testable components
8. **User Experience**: Natural language interface that adapts to user communication style

---

## Technology Stack

- **Backend**: Python 3.9+, Flask
- **Database**: Supabase (PostgreSQL)
- **NLP**: Google Gemini API (multiple model options)
- **SMS**: Twilio API
- **Scheduling**: APScheduler
- **Authentication**: bcrypt, Flask sessions
- **Encryption**: Fernet (cryptography library)
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Deployment**: Ready for containerization (Docker), cloud deployment

---

## Future Enhancements

The architecture supports easy addition of:

- **New Integrations**: Plugin-based integration system
- **New Intents**: Handler-based intent system
- **Advanced Learning**: Machine learning model integration
- **Real-Time Features**: WebSocket support for live updates
- **Mobile App**: API-ready for mobile application
- **Analytics**: Built-in data collection for analytics
- **Multi-Language**: NLP system supports multiple languages

---

This technical architecture represents a production-grade system with careful attention to scalability, maintainability, security, and user experience. The modular design enables independent development and testing of components while maintaining a cohesive user experience across all interaction channels.
