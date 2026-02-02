"""
SMS Onboarding Flow (Account-First)

This module handles the SMS onboarding state machine for users who already
exist in the database (signed up on web) but haven't completed onboarding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass(frozen=True)
class OnboardingResult:
    reply: Union[str, List[str]]
    # If True, onboarding has fully completed this turn
    completed: bool = False


def _normalize(text: str) -> str:
    return (text or "").strip()


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


def handle_onboarding(
    *,
    message: str,
    user: Dict[str, Any],
    session: Dict[str, Any],
    config_default_bottle_ml: int,
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

    if step == 0:
        session["onboarding_step"] = 1
        return (
            OnboardingResult(
                reply=[
                    f"Hey {first_name}! Good to hear from you.",
                    "Let me ask you a couple things so I can be useful right away.\n\n" + reminder_style_question,
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
        user_updates["reminder_style_raw"] = raw
        user_updates["reminder_style_bucket"] = map_reminder_style_bucket(raw)
        session["onboarding_step"] = 2
        return (
            OnboardingResult(
                reply="How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
            ),
            user_updates,
            prefs_updates,
        )

    if step == 2:
        raw = _normalize(message)
        if not raw:
            return (
                OnboardingResult(
                    reply="How should I sound when I text you? Chill and casual, polished and preppy, or something else entirely? Whatever you prefer, we'll run with it."
                ),
                user_updates,
                prefs_updates,
            )
        user_updates["voice_style_raw"] = raw
        user_updates["voice_style_bucket"] = map_voice_style_bucket(raw)
        session["onboarding_step"] = 3
        return (
            OnboardingResult(
                reply="How big is your usual water bottle? (e.g. 500ml, 16oz, 1L, or 'standard' if you're not sure)"
            ),
            user_updates,
            prefs_updates,
        )

    if step == 3:
        raw = _normalize(message)
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
        return (
            OnboardingResult(
                reply="What time do you want your daily morning text? It'll include your reminders and todos for the day, the weather, and a motivational quote. You can mix and match what you want in it later—just tell me."
            ),
            user_updates,
            prefs_updates,
        )

    if step == 4:
        raw = _normalize(message)
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
        return (
            OnboardingResult(
                reply="All set. I'll keep that in mind. Text me anything—try 'remind me to call Mom at 5' or 'drank a bottle.' Say 'help' whenever you need it.",
                completed=True,
            ),
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

