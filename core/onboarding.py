"""
SMS Onboarding Flow (Account-First)

This module handles the SMS onboarding state machine for users who already
exist in the database (signed up on web) but haven't completed onboarding.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


def _preferences_link() -> str:
    """Base URL + /dashboard/preferences for post-onboarding message."""
    base = (os.getenv("BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "http://localhost:5001").strip().rstrip("/")
    return f"{base}/dashboard/preferences"


@dataclass(frozen=True)
class OnboardingResult:
    reply: Union[str, List[str]]
    # If True, onboarding has fully completed this turn
    completed: bool = False


def _normalize(text: str) -> str:
    return (text or "").strip()


def _reflect_back(raw: str, max_len: int = 100) -> str:
    """Short summary of user's answer (e.g. for water bottle size display). Not used for reminder/voice—we use bucket synthesis instead."""
    s = (raw or "").strip()
    if not s:
        return "that"
    for end in (". ", "! ", "?\n", ".\n"):
        i = s.find(end)
        if i != -1:
            s = s[: i + 1].strip()
            break
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s


# Short synthesis of what each reminder-style bucket means (we say this back, we don't quote the user)
REMINDER_BUCKET_SYNTHESIS: Dict[str, str] = {
    "very_persistent": "you want me in your ear a lot—constant check-ins and follow-ups",
    "persistent": "you want regular check-ins and follow-ups to stay on track",
    "only_critical": "you only want a nudge when something's really important",
    "minimal": "you want me to stay out of your way and only chime in when you need me",
    "relaxed": "you want it light—gentle nudges, no pressure",
    "moderate": "you want a moderate level—not too many reminders, but you do want me to bug you when it really matters",
}

# How Alfred will behave based on reminder-style bucket
REMINDER_BUCKET_BEHAVIOR: Dict[str, str] = {
    "very_persistent": "I'll check in often and follow up so you stay on track.",
    "persistent": "I'll keep you on track with regular check-ins and follow-ups.",
    "only_critical": "I'll only bug you when something's really important.",
    "minimal": "I'll stay out of your way and only chime in when you need me.",
    "relaxed": "I'll keep it light—gentle nudges, no pressure.",
    "moderate": "I'll nudge you when it matters but won't overdo it.",
}

# Short synthesis of what each voice-style bucket means (we say this back, we don't quote the user)
VOICE_BUCKET_SYNTHESIS: Dict[str, str] = {
    "very_formal": "you want me to sound very formal and professional",
    "formal": "you want a professional, proper tone",
    "polished": "you want me clean and preppy",
    "neutral": "you want a natural, balanced tone",
    "friendly_casual": "you want me warm and friendly",
    "casual": "you want me chill and casual",
    "other": "you've got a particular vibe in mind",
}

# How Alfred will sound based on voice-style bucket
VOICE_BUCKET_BEHAVIOR: Dict[str, str] = {
    "very_formal": "I'll keep things formal and professional.",
    "formal": "I'll sound professional and polished.",
    "polished": "I'll keep it clean and preppy.",
    "neutral": "I'll keep it natural and balanced.",
    "friendly_casual": "I'll be warm and friendly.",
    "casual": "I'll keep it chill and casual.",
    "other": "I'll match the vibe you described.",
}


def map_reminder_style_bucket(raw: str) -> str:
    t = raw.lower()
    if any(k in t for k in ["always", "constantly", "all the time", "aggressive", "pushy", "on my case"]):
        return "very_persistent"
    if any(k in t for k in ["often", "frequent", "regular", "keep me on track", "follow up a lot"]):
        return "persistent"
    if any(k in t for k in ["only important", "only when it matters", "important stuff", "critical", "urgent only"]):
        return "only_critical"
    if any(k in t for k in ["minimal", "rare", "barely", "don't remind", "no nudges"]):
        return "minimal"
    if any(k in t for k in ["relaxed", "chill", "light", "gentle"]):
        return "relaxed"
    return "moderate"


def map_voice_style_bucket(raw: str) -> str:
    t = raw.lower()
    if any(k in t for k in ["very formal", "extremely formal"]):
        return "very_formal"
    if any(k in t for k in ["formal", "professional", "proper"]):
        return "formal"
    if any(k in t for k in ["polished", "preppy", "clean", "crisp"]):
        return "polished"
    if any(k in t for k in ["neutral", "normal", "just be yourself"]):
        return "neutral"
    if any(k in t for k in ["friendly", "warm"]):
        return "friendly_casual"
    if any(k in t for k in ["chill", "casual", "laid back", "laid-back", "slang"]):
        return "casual"
    return "other"


def parse_volume_to_ml(raw: str) -> Optional[int]:
    """
    Parse a volume string like:
    - 500ml, 710 ml
    - 16oz, 16 oz
    - 1L, 1 liter
    """
    t = raw.lower().strip()
    if not t:
        return None
    if "standard" in t or "default" in t:
        return None

    # liters
    m = re.search(r"(\d+(?:\.\d+)?)\s*(l|liter|litre|liters|litres)\b", t)
    if m:
        return int(float(m.group(1)) * 1000)

    # ml
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", t)
    if m:
        return int(float(m.group(1)))

    # oz (US fluid ounces)
    m = re.search(r"(\d+(?:\.\d+)?)\s*oz\b", t)
    if m:
        return int(float(m.group(1)) * 29.5735)

    return None


def parse_hour_0_23(raw: str) -> Optional[int]:
    """
    Parse a time-of-day into an hour (0-23).
    Accepts: "8", "8am", "8 pm", "20", "20:00", "8:30am"
    """
    t = raw.lower().strip()
    if not t:
        return None

    # 24h like 20 or 20:30
    m = re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))\b", t)
    if m and ("am" not in t and "pm" not in t):
        return int(m.group(1))

    # 12h with am/pm, optional minutes
    m = re.search(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(am|pm)\b", t)
    if m:
        hour = int(m.group(1))
        ampm = m.group(3)
        if ampm == "am":
            return 0 if hour == 12 else hour
        return 12 if hour == 12 else hour + 12

    # bare number (assume morning for 6-11, else treat as 24h if plausible)
    m = re.search(r"\b(\d{1,2})\b", t)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return hour
    return None


# Intents that mean the user is not answering the current onboarding question (log food, say hi, ask for suggestion, etc.)
OFF_TOPIC_ONBOARDING_INTENTS = frozenset({
    "greeting", "chitchat", "food_logging", "water_logging", "gym_workout", "sleep_logging",
    "reminder_set", "todo_add", "assignment_add", "stats_query", "fact_storage", "fact_query",
    "what_should_i_do", "food_suggestion", "task_complete", "vague_completion", "undo_edit",
    "confirmation", "integration_manage",
})

ONBOARDING_REDIRECT = (
    "Finishing these quick questions will make your experience much smoother. "
    "Let's get through them first—then you can log food, ask for suggestions, or do anything else.\n\n"
)

# Phrases that mean the user wants to skip the current step (we advance with a sensible default)
SKIP_PHRASES = frozenset({
    "skip", "later", "not sure", "idk", "i don't know", "dunno", "not now", "pass",
    "maybe later", "next", "nope", "no idea", "whatever", "default", "you choose",
})


def _is_skip(message: str) -> bool:
    """True if the message looks like the user wants to skip (e.g. 'skip', 'later', 'not sure')."""
    t = _normalize(message).lower()
    if not t:
        return False
    if t in SKIP_PHRASES:
        return True
    # "I'll do it later", "not sure yet", etc.
    if len(t) <= 25 and any(p in t for p in SKIP_PHRASES):
        return True
    return False


def handle_onboarding(
    *,
    message: str,
    user: Dict[str, Any],
    session: Dict[str, Any],
    config_default_bottle_ml: int,
    classified_intent: Optional[str] = None,
) -> Tuple[OnboardingResult, Dict[str, Any], Dict[str, Any]]:
    """
    Returns:
    - OnboardingResult (reply + completed)
    - user_updates dict to persist on users
    - prefs_updates dict to persist on user_preferences (currently empty; reserved)
    """
    # Steps:
    # 0 welcome -> 1
    # 1 reminder style -> 2
    # 2 voice style -> 3
    # 3 water bottle -> 4
    # 4 morning check-in -> 5 (done)
    # 5 done -> mark onboarding complete, clear

    step = session.get("onboarding_step")
    if step is None:
        step = 0

    full_name = (user.get("name") or "").strip()
    first_name = (full_name.split()[0] if full_name else "").strip() or "there"
    reminder_style_question = (
        "How much do you want me in your ear? Some people like constant check-ins and follow-ups; "
        "others only want a nudge when it really matters. However you'd describe it—tell me."
    )

    user_updates: Dict[str, Any] = {}
    prefs_updates: Dict[str, Any] = {}

    # If the message is clearly off-topic (e.g. "ate a quesadilla", "hi"), redirect and re-ask current question
    if classified_intent and classified_intent in OFF_TOPIC_ONBOARDING_INTENTS:
        if step == 1:
            return (
                OnboardingResult(reply=ONBOARDING_REDIRECT + reminder_style_question),
                user_updates,
                prefs_updates,
            )
        voice_style_question = "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
        if step == 2:
            return (
                OnboardingResult(reply=ONBOARDING_REDIRECT + voice_style_question),
                user_updates,
                prefs_updates,
            )
        if step == 3:
            water_question = "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"
            return (
                OnboardingResult(reply=ONBOARDING_REDIRECT + water_question),
                user_updates,
                prefs_updates,
            )
        if step == 4:
            morning_question = "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."
            return (
                OnboardingResult(reply=ONBOARDING_REDIRECT + morning_question),
                user_updates,
                prefs_updates,
            )

    if step == 0:
        session["onboarding_step"] = 1
        return (
            OnboardingResult(
                reply=[
                    f"Hey {first_name}! Good to hear from you.",
                    "Finishing this will make your experience much smoother. Let me ask you a couple things so I can be useful right away.\n\n" + reminder_style_question,
                ]
            ),
            user_updates,
            prefs_updates,
        )

    if step == 1:
        raw = _normalize(message)
        if not raw:
            return (
                OnboardingResult(
                    reply=reminder_style_question
                ),
                user_updates,
                prefs_updates,
            )
        if _is_skip(message):
            user_updates["reminder_style_raw"] = "(skipped)"
            user_updates["reminder_style_bucket"] = "moderate"
            session["onboarding_step"] = 2
            next_question = "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
            reply = "No problem — I'll go with a moderate level. You can change it later in settings.\n\n" + next_question
            return (OnboardingResult(reply=reply), user_updates, prefs_updates)
        bucket = map_reminder_style_bucket(raw)
        user_updates["reminder_style_raw"] = raw
        user_updates["reminder_style_bucket"] = bucket
        session["onboarding_step"] = 2
        synthesis = REMINDER_BUCKET_SYNTHESIS.get(bucket, REMINDER_BUCKET_SYNTHESIS["moderate"])
        behavior = REMINDER_BUCKET_BEHAVIOR.get(bucket, REMINDER_BUCKET_BEHAVIOR["moderate"])
        next_question = "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
        reply = f"Got it — so {synthesis}. {behavior}\n\n{next_question}"
        return (
            OnboardingResult(reply=reply),
            user_updates,
            prefs_updates,
        )

    voice_style_question = "How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
    if step == 2:
        raw = _normalize(message)
        if not raw:
            return (
                OnboardingResult(reply=voice_style_question),
                user_updates,
                prefs_updates,
            )
        if _is_skip(message):
            user_updates["voice_style_raw"] = "(skipped)"
            user_updates["voice_style_bucket"] = "neutral"
            session["onboarding_step"] = 3
            next_question = "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"
            reply = "No problem — I'll keep it natural. You can change it later in settings.\n\n" + next_question
            return (OnboardingResult(reply=reply), user_updates, prefs_updates)
        bucket = map_voice_style_bucket(raw)
        user_updates["voice_style_raw"] = raw
        user_updates["voice_style_bucket"] = bucket
        session["onboarding_step"] = 3
        synthesis = VOICE_BUCKET_SYNTHESIS.get(bucket, VOICE_BUCKET_SYNTHESIS["other"])
        behavior = VOICE_BUCKET_BEHAVIOR.get(bucket, VOICE_BUCKET_BEHAVIOR["other"])
        next_question = "How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"
        reply = f"Got it — so {synthesis}. {behavior}\n\n{next_question}"
        return (
            OnboardingResult(reply=reply),
            user_updates,
            prefs_updates,
        )

    if step == 3:
        raw = _normalize(message)
        if _is_skip(message):
            user_updates["water_bottle_ml"] = int(config_default_bottle_ml)
            session["onboarding_step"] = 4
            next_question = "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."
            reply = "No problem — I'll use a standard bottle size. You can change it later in settings.\n\n" + next_question
            return (OnboardingResult(reply=reply), user_updates, prefs_updates)
        ml = parse_volume_to_ml(raw)
        if ml is None:
            # If user typed "standard", accept and use default
            if raw and ("standard" in raw.lower() or "default" in raw.lower()):
                ml = int(config_default_bottle_ml)
            else:
                return (
                    OnboardingResult(
                        reply="Got it—about how big is it? Examples: 500ml, 16oz, 750ml, 1L (or say 'standard')."
                    ),
                    user_updates,
                    prefs_updates,
                )
        user_updates["water_bottle_ml"] = int(ml)
        session["onboarding_step"] = 4
        # Confirm: reflect back (e.g. "500ml" or "one standard bottle") and how we'll use it
        if raw and ("standard" in raw.lower() or "default" in raw.lower()):
            summary = "one standard bottle"
        else:
            summary = raw if len(raw) <= 30 else _reflect_back(raw, max_len=30)
        next_question = "What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."
        reply = f"Got it — so that's {summary}. I'll use that when you say things like \"drank a bottle\" or \"had two bottles.\"\n\n{next_question}"
        return (
            OnboardingResult(reply=reply),
            user_updates,
            prefs_updates,
        )

    if step == 4:
        raw = _normalize(message)
        if _is_skip(message):
            user_updates["morning_checkin_hour"] = 8  # 8am default
            user_updates["onboarding_complete"] = True
            session.pop("onboarding_step", None)
            prefs_url = _preferences_link()
            reply = (
                "No problem — I'll send it at 8am. You can change it later in settings. All set. Text me anything—try \"remind me to call Mom at 5\" or \"drank a bottle.\" Say \"help\" whenever you need it.\n\n"
                f"There are more preferences you can set to make your experience smoother—you can find them here! {prefs_url}"
            )
            return (OnboardingResult(reply=reply, completed=True), user_updates, prefs_updates)
        hour = parse_hour_0_23(raw)
        if hour is None:
            return (
                OnboardingResult(
                    reply="What time works? Examples: 8am, 9am, 7, 20 (for 8pm)."
                ),
                user_updates,
                prefs_updates,
            )
        user_updates["morning_checkin_hour"] = int(hour)
        user_updates["onboarding_complete"] = True
        session.pop("onboarding_step", None)
        # Confirm morning time in human form (e.g. 8am, 8pm)
        if hour == 0:
            time_str = "midnight"
        elif hour == 12:
            time_str = "noon"
        elif hour < 12:
            time_str = f"{hour}am"
        else:
            time_str = f"{hour - 12}pm"
        prefs_url = _preferences_link()
        reply = (
            f"Got it — I'll send your daily morning text at {time_str}. All set. Text me anything—try \"remind me to call Mom at 5\" or \"drank a bottle.\" Say \"help\" whenever you need it.\n\n"
            f"There are more preferences you can set to make your experience smoother—you can find them here! {prefs_url}"
        )
        return (
            OnboardingResult(reply=reply, completed=True),
            user_updates,
            prefs_updates,
        )

    # Fallback: reset onboarding
    session["onboarding_step"] = 0
    return (
        OnboardingResult(
            reply=f"Hey {first_name}! Let's get you set up. (If I ever lose my place, just say anything and I'll pick back up.)"
        ),
        user_updates,
        prefs_updates,
    )

