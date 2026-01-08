# SMS Assistant

**Your personal productivity assistant that lives in your text messages.** No apps to open, no dashboards to check—just text what you did, what you need, or what you want to know. Powered by advanced NLP and designed to understand you, not just respond to commands.

## Why This Exists

Most productivity tools require you to adapt to them. This one adapts to you. Text naturally, make mistakes, be vague—it figures it out. After a long workout, just text "done" and it'll ask what you meant. Forget to respond to a reminder? It'll check back with you. Your todo list getting stale? It'll help you clean it up. This isn't just logging—it's an intelligent system that actually helps you stay on track.

## Architecture

```
┌─────────────┐
│   Twilio    │
│   SMS API   │
└──────┬──────┘
       │
       │ HTTP POST (TwiML)
       ▼
┌─────────────────────────────────────┐
│         Flask Application           │
│  ┌───────────────────────────────┐ │
│  │  Message Processor             │ │
│  │  - Intent Classification       │ │
│  │  - Entity Extraction           │ │
│  └───────────┬─────────────────────┘ │
│              │                        │
│  ┌───────────▼─────────────────────┐ │
│  │  Gemini NLP Processor           │ │
│  │  (Gemma-3-12b-it)               │ │
│  └───────────┬─────────────────────┘ │
│              │                        │
│  ┌───────────▼─────────────────────┐ │
│  │  Supabase Database              │ │
│  │  - Food logs                    │ │
│  │  - Water logs                   │ │
│  │  - Gym logs                     │ │
│  │  - Reminders/Todos              │ │
│  │  - Assignments                  │ │
│  │  - Sleep logs                   │ │
│  │  - Facts/Information            │ │
│  └─────────────────────────────────┘ │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │  Background Scheduler           │ │
│  │  - Reminder checks              │ │
│  │  - Follow-ups                   │ │
│  │  - Weekly digests               │ │
│  │  - Gentle nudges                │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
       │
       │ (optional)
       ▼
┌─────────────┐
│   Google    │
│  Calendar   │
└─────────────┘
```

## Core Features

### Natural Language Everything

Forget rigid commands. Text "drank a bottle" or "had a quesadilla" or "did bench press 135 for 5" and it understands. The system uses Google's Gemini API to parse intent and extract entities, so you can phrase things your way. It learns your patterns and gets smarter over time.

### Smart Context Awareness

Ask "what should I do now?" and it synthesizes everything: your incomplete todos, upcoming calendar events, water intake status, meal timing, and time of day to suggest what actually makes sense right now. It's like having a personal assistant that actually knows your situation.

### "What Just Happened?" Mode

Text "just finished" or "done" when you're exhausted, and instead of guessing, it shows you a numbered list of likely interpretations based on your recent activity. Pick a number. Done. This feature alone saves mental energy when you're drained after a workout or late-night session.

### Intelligent Reminder System

Reminders don't just fire and forget. If you don't respond, the system checks back with a gentle follow-up. Missed a reminder? It proactively suggests rescheduling with quick options. The system treats reminders as open loops that deserve closure, not notifications to ignore.

### Task Decay & Cleanup

Your todo list won't become a forgotten archive. The system periodically reviews stale tasks and asks if they're still relevant. Keep it, reschedule it, or delete it—your choice. This keeps your task list meaningful and prevents silent clutter buildup.

### Weekly Digest

Every week, get a compact summary of your behavior: water averages, gym frequency, food patterns, task completion rates. Skimmable in 30 seconds, insightful without dashboards. Passive reflection that builds self-awareness with zero effort.

### Gentle Nudges

Instead of "Drink water now," you get "You're one bottle behind your usual pace today." Context-aware nudges that reference your personal patterns, not absolute goals. They're informative, non-judgmental, and harder to ignore because they feel helpful, not demanding.

### Undo & Edit

Made a mistake? Text "undo last water" or "delete last food" and it's gone. No hunting through files or reissuing complex commands. This makes logging feel safe—you can always fix it later, which encourages more consistent use.

### Google Calendar Integration

Optional but powerful. The system reads your calendar and shows events alongside reminders and todos. Ask "what do I have today?" and get everything in one place. Schedule awareness without switching apps.

### Custom Food Database

Log meals with automatic macro tracking from your custom food database. Same food from different restaurants? Different macros. The system handles portion multipliers, restaurant-specific entries, and learns your eating patterns.

### Assignment Tracking

Track school assignments with class names and due dates. Text "CS101 homework 3 due Friday" or "Math assignment due tomorrow" and the system automatically extracts the class, assignment name, and due date. Assignments appear in your morning check-ins and dashboard, helping you stay on top of deadlines.

## What Makes This Different

**It's forgiving.** Make mistakes, be vague, forget to respond—the system handles it gracefully.

**It's proactive.** It doesn't just log what you tell it; it follows up, suggests, and helps you stay on track.

**It's intelligent.** Uses advanced NLP to understand natural language, not just parse commands.

**It's context-aware.** Suggestions and responses consider your current situation, not just your data.

**It's low-friction.** Everything happens over SMS. No apps, no dashboards, no extra steps.

**It learns.** The system adapts to your patterns and gets better at understanding you over time.

## Quick Examples

**Logging:**
- `"drank a bottle"` → Logs water, shows daily total and goal progress
- `"ate sazon quesadilla"` → Logs food with macros from your database
- `"did bench press 135x5"` → Logs workout with all details

**Tasks:**
- `"remind me to call mom at 3pm"` → Sets time-based reminder
- `"todo buy groceries"` → Adds to your list
- `"CS101 homework 3 due Friday"` → Adds assignment with class, name, and due date
- `"called mom"` → Intelligently matches and completes the task

**Queries:**
- `"how much have I eaten"` → Daily food totals with macros
- `"what do I have to do today"` → Todos, reminders, assignments, and calendar events
- `"what should I do now"` → Context-aware suggestions based on your situation

**Smart Features:**
- `"just finished"` → Shows numbered options of what you might mean
- `"undo last water"` → Removes last entry instantly
- Weekly digest sent automatically every Monday

## Technical Stack

- **Flask** - Web framework for Twilio webhooks
- **Twilio** - SMS API for messaging
- **Google Gemini API (Gemma-3-12b-it)** - Natural language processing
- **Supabase** - PostgreSQL database for persistent storage
- **APScheduler** - Background task scheduling
- **Google Calendar API** - Calendar integration

## Viewing Stats
Go to https://objective-almeria-sarthakagrawal-a8b1c327.koyeb.app/dashboard/login and use the correct password to view daily stats as well as 7, 30, and 90 day trends

## License

See LICENSE file for details.