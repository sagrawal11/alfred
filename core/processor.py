"""
Message Processor
Main message processing engine that coordinates NLP, handlers, and responses
"""

import os
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from nlp import (
    create_llm_client, IntentClassifier, EntityExtractor,
    Parser, PatternMatcher, DatabaseLoader
)
from data import (
    UserRepository, KnowledgeRepository, UserPreferencesRepository
)
from core.context import ConversationContext
from core.session import SessionManager
from core.onboarding import handle_onboarding
from learning import LearningOrchestrator
from handlers.base_handler import BaseHandler
from handlers.food_handler import FoodHandler
from handlers.water_handler import WaterHandler
from handlers.gym_handler import GymHandler
from handlers.todo_handler import TodoHandler
from handlers.query_handler import QueryHandler
from handlers.integration_handler import IntegrationHandler
from responses.formatter import ResponseFormatter
from integrations import IntegrationAuthManager, SyncManager
from data import IntegrationRepository
from services.nutrition import NutritionResolver


class MessageProcessor:
    """Main message processing engine"""
    
    def __init__(self, supabase):
        """
        Initialize message processor
        
        Args:
            supabase: Supabase client
        """
        self.supabase = supabase
        
        # Initialize NLP components
        self.llm_client = create_llm_client()
        self.db_loader = DatabaseLoader()
        self.intent_classifier = IntentClassifier(self.llm_client)
        self.entity_extractor = EntityExtractor(self.llm_client)
        self.nutrition_resolver = NutritionResolver(self.supabase)
        self.parser = Parser(self.llm_client, self.db_loader, nutrition_resolver=self.nutrition_resolver)
        
        # Initialize repositories
        self.user_repo = UserRepository(supabase)
        self.knowledge_repo = KnowledgeRepository(supabase)
        self.user_prefs_repo = UserPreferencesRepository(supabase)
        
        # Initialize integration components
        self.integration_repo = IntegrationRepository(supabase)
        self.integration_auth = IntegrationAuthManager(supabase, self.integration_repo)
        self.sync_manager = SyncManager(supabase, self.integration_repo, self.integration_auth)
        
        # Initialize pattern matcher (for learning system)
        self.pattern_matcher = PatternMatcher(self.knowledge_repo)
        
        # Initialize learning orchestrator
        self.learning_orchestrator = LearningOrchestrator(self.knowledge_repo)
        
        # Initialize session manager
        self.session_manager = SessionManager(supabase)
        
        # Initialize response formatter
        self.formatter = ResponseFormatter()
        
        # Initialize handlers
        self.handlers: Dict[str, BaseHandler] = {
            'food_logging': FoodHandler(supabase, self.parser, self.formatter),
            'water_logging': WaterHandler(supabase, self.parser, self.formatter),
            'gym_workout': GymHandler(supabase, self.parser, self.formatter),
            'todo_add': TodoHandler(supabase, self.parser, self.formatter),
            'reminder_set': TodoHandler(supabase, self.parser, self.formatter),  # Same handler
            'assignment_add': TodoHandler(supabase, self.parser, self.formatter),  # Same handler
            'stats_query': QueryHandler(supabase, self.parser, self.formatter),
            'fact_storage': QueryHandler(supabase, self.parser, self.formatter),  # Same handler
            'fact_query': QueryHandler(supabase, self.parser, self.formatter),  # Same handler
            'integration_manage': IntegrationHandler(supabase, self.integration_repo, 
                                                   self.integration_auth, self.sync_manager, 
                                                   self.formatter),
        }
    
    def process_message(self, message: str, phone_number: str, user_id: Optional[int] = None) -> Union[str, List[str]]:
        """
        Process an incoming message
        
        Args:
            message: Message text
            phone_number: Sender's phone number (E.164 format)
            
        Returns:
            Response text. In a few cases (onboarding), this can be a list of SMS-sized messages.
        """
        try:
            message_clean = (message or "").strip()
            message_lower = message_clean.lower()

            # Dashboard chat can pass a placeholder phone; support deriving user_id from it
            if user_id is None and phone_number and phone_number.startswith("web-user-"):
                try:
                    user_id = int(phone_number.split("web-user-", 1)[1])
                except Exception:
                    user_id = None

            # Look up user (NO auto-creation for unknown phone numbers)
            user: Optional[Dict[str, Any]] = None
            if user_id is not None:
                user = self.user_repo.get_by_id(user_id)
            if user is None:
                user = self.user_repo.get_by_phone(phone_number)

            # STOP/HELP should work even if user doesn't exist yet
            if message_lower in ["help", "info"]:
                return (
                    "This is a personal SMS assistant operated by Sarthak Agrawal. "
                    "It sends reminders, notifications, and assistant responses after you opt in. "
                    "Reply STOP to opt out at any time."
                )

            if message_lower == "stop":
                if user:
                    self.user_repo.deactivate_user(user["id"])
                return (
                    "You have been unsubscribed from messages from Sarthak Agrawal. "
                    "You will no longer receive SMS messages. Reply START to re-subscribe."
                )

            if message_lower == "start":
                if user and not user.get("is_active", True):
                    self.user_repo.activate_user(user["id"])
                    return "You're re-subscribed. Text me anything to get started."
                # If they're not in DB yet, treat as text-first and send signup link below.

            # If no account exists yet for this phone number, guide them to signup
            if not user:
                base_url = os.getenv("BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "http://localhost:5001"
                signup_link = base_url.rstrip("/") + "/"
                return (
                    "Hey! You're not signed up yet. Alfred works best when we're connected—"
                    f"create an account at {signup_link}, then text this number again and we'll get you set up."
                )

            # Respect opt-out / deactivated accounts
            if not user.get("is_active", True):
                return "You're unsubscribed. Reply START to re-subscribe, or HELP for more info."
            
            user_id = user['id']

            # Ensure preferences row exists (safe no-op if present)
            try:
                self.user_prefs_repo.ensure(user_id)
            except Exception:
                # Don't fail processing if prefs can't be created (RLS/migration issues)
                pass
            
            # Get session
            session = self.session_manager.get_session(user_id)

            # Onboarding (account-first): run before confirmations/NLP
            if not user.get("onboarding_complete", False):
                result, user_updates, prefs_updates = handle_onboarding(
                    message=message_clean,
                    user=user,
                    session=session,
                    config_default_bottle_ml=int(self.db_loader.water_bottle_size_ml),
                )
                if user_updates:
                    try:
                        self.user_repo.update(user_id, user_updates)
                        # reflect latest fields locally for subsequent checks this request
                        user.update(user_updates)
                    except Exception as e:
                        print(f"Error persisting onboarding user updates: {e}")
                if prefs_updates:
                    try:
                        self.user_prefs_repo.update(user_id, prefs_updates)
                    except Exception as e:
                        print(f"Error persisting onboarding prefs updates: {e}")
                return result.reply

            # Lightweight preference commands (avoid expensive NLP when possible)
            pref_response = self._handle_preference_commands(message_clean, message_lower, user_id, user)
            if pref_response:
                return pref_response
            
            # Check for pending confirmations/selections first
            if 'pending_confirmations' in session and session['pending_confirmations']:
                response = self._handle_pending_confirmation(message, user_id, session)
                if response:
                    return response
            
            # Step 1: Apply learned patterns BEFORE NLP (to enhance classification)
            suggested_intent, suggested_entities = self.learning_orchestrator.apply_learned_patterns(
                user_id, message
            )
            
            # Step 2: Classify intent (use learned pattern if high confidence, otherwise use NLP)
            intent = suggested_intent if suggested_intent else self.intent_classifier.classify(message)
            
            # Step 3: Extract entities
            entities = self.entity_extractor.extract(message)
            
            # Step 4: Merge learned pattern entities
            if suggested_entities:
                for key, values in suggested_entities.items():
                    if key not in entities:
                        entities[key] = []
                    entities[key].extend([v['value'] for v in values])
            
            print(f"Intent: {intent}, Entities: {entities}")
            
            # Get conversation context
            from data import (
                FoodRepository, WaterRepository, GymRepository,
                TodoRepository, SleepRepository, AssignmentRepository
            )
            
            context = ConversationContext(
                user_id=user_id,
                food_repo=FoodRepository(self.supabase),
                water_repo=WaterRepository(self.supabase),
                gym_repo=GymRepository(self.supabase),
                todo_repo=TodoRepository(self.supabase),
                sleep_repo=SleepRepository(self.supabase),
                assignment_repo=AssignmentRepository(self.supabase)
            )
            
            # Step 5: Route to appropriate handler
            handler = self.handlers.get(intent)
            processing_result = None
            response = None
            
            if handler:
                response = handler.handle(message, intent, entities, user_id, context)
                if response:
                    # Mark as successful processing
                    processing_result = {'success': True, 'intent': intent}
                    
                    # Step 6: Learn from successful processing
                    learned_patterns = self.learning_orchestrator.process_message_for_learning(
                        user_id=user_id,
                        message=message,
                        intent=intent,
                        entities=entities,
                        result=processing_result
                    )
                    
                    # Record pattern usage if we used a learned pattern
                    if suggested_intent:
                        # Extract key terms from message
                        from learning.pattern_extractor import PatternExtractor
                        extractor = PatternExtractor()
                        key_terms = extractor._extract_key_terms(message)
                        
                        for term in key_terms:
                            if len(term) > 3:
                                self.learning_orchestrator.record_pattern_usage(
                                    user_id=user_id,
                                    pattern_term=term,
                                    pattern_type='intent',
                                    associated_value=intent,
                                    success=True
                                )
                    
                    # Update session
                    session['conversation_history'].append({
                        'message': message,
                        'intent': intent,
                        'response': response,
                        'timestamp': datetime.now().isoformat()
                    })
                    # Keep only last 10 messages
                    if len(session['conversation_history']) > 10:
                        session['conversation_history'] = session['conversation_history'][-10:]
                    
                    return response
            
            # Fallback for unknown intents
            return self.formatter.format_fallback(message)
            
        except Exception as e:
            print(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            return self.formatter.format_error()
    
    def _handle_pending_confirmation(self, message: str, user_id: int, session: Dict) -> Optional[str]:
        """Handle pending confirmation responses"""
        pending = session['pending_confirmations']
        
        # Check if message is a confirmation
        message_lower = message.lower().strip()
        if message_lower in ['yes', 'yep', 'y', 'correct', 'ok', 'okay']:
            # Execute pending action
            action = pending.get('action')
            if action:
                # Handler will process the confirmation
                handler = self.handlers.get(pending.get('intent'))
                if handler:
                    return handler.handle_confirmation(message, user_id, pending)
            
            # Clear pending confirmation
            session['pending_confirmations'] = {}
            return "Got it! Action completed."
        elif message_lower in ['no', 'nope', 'n', 'cancel']:
            # Clear pending confirmation
            session['pending_confirmations'] = {}
            return "Okay, cancelled."
        
        return None

    def _handle_preference_commands(
        self,
        message: str,
        message_lower: str,
        user_id: int,
        user: Dict[str, Any],
    ) -> Optional[str]:
        """
        Handle simple preference updates without running Gemini.
        Returns a reply string if handled, else None.
        """
        # Morning message toggles
        if "morning" in message_lower and ("text" in message_lower or "message" in message_lower):
            updates: Dict[str, Any] = {}
            ack_parts: list[str] = []

            def wants_disable() -> bool:
                return any(k in message_lower for k in ["don't", "dont", "no ", "remove", "stop", "without"])

            disable = wants_disable()

            if "weather" in message_lower:
                updates["morning_include_weather"] = not disable
                ack_parts.append(("stop" if disable else "start") + " including weather")
            if "quote" in message_lower:
                updates["morning_include_quote"] = not disable
                ack_parts.append(("stop" if disable else "start") + " including the quote")
            if "reminder" in message_lower or "todo" in message_lower or "tasks" in message_lower:
                updates["morning_include_reminders"] = not disable
                ack_parts.append(("stop" if disable else "start") + " including reminders/todos")

            if updates:
                try:
                    self.user_prefs_repo.update(user_id, updates)
                except Exception as e:
                    print(f"Error updating morning toggles: {e}")
                    return self.formatter.format_error("Couldn't update morning message settings yet")

                return "Got it — I'll " + ", and I'll ".join(ack_parts) + " in your morning text."

        # Units (metric/imperial)
        if "units" in message_lower or "metric" in message_lower or "imperial" in message_lower:
            units = None
            if "imperial" in message_lower or "us units" in message_lower or "oz" in message_lower:
                units = "imperial"
            if "metric" in message_lower or "ml" in message_lower:
                units = "metric"
            if units:
                try:
                    self.user_prefs_repo.update(user_id, {"units": units})
                except Exception as e:
                    print(f"Error updating units: {e}")
                    return self.formatter.format_error("Couldn't update units yet")
                return f"Done — I'll use {units} units in messages."

        # Quiet hours / do not disturb (e.g. "quiet hours 10pm-7am")
        if "quiet hours" in message_lower or "do not disturb" in message_lower or "dnd" in message_lower:
            from core.onboarding import parse_hour_0_23
            # crude parse: take first two time-like tokens
            tokens = [t.strip() for t in re.split(r"[\s,]+", message_lower) if t.strip()]
            hours: list[int] = []
            for tok in tokens:
                h = parse_hour_0_23(tok)
                if h is not None:
                    hours.append(int(h))
                if len(hours) >= 2:
                    break
            if len(hours) >= 2:
                start, end = hours[0], hours[1]
                try:
                    self.user_prefs_repo.update(user_id, {"quiet_hours_start": start, "quiet_hours_end": end, "do_not_disturb": False})
                except Exception as e:
                    print(f"Error updating quiet hours: {e}")
                    return self.formatter.format_error("Couldn't update quiet hours yet")
                return f"Got it — I'll stay quiet from {start:02d}:00 to {end:02d}:00 (your local time)."
            if "on" in message_lower and ("dnd" in message_lower or "do not disturb" in message_lower):
                try:
                    self.user_prefs_repo.update(user_id, {"do_not_disturb": True})
                except Exception as e:
                    print(f"Error enabling DND: {e}")
                    return self.formatter.format_error("Couldn't enable do-not-disturb yet")
                return "Okay — do-not-disturb is on. Reply 'dnd off' to re-enable messages."
            if "off" in message_lower and ("dnd" in message_lower or "do not disturb" in message_lower):
                try:
                    self.user_prefs_repo.update(user_id, {"do_not_disturb": False})
                except Exception as e:
                    print(f"Error disabling DND: {e}")
                    return self.formatter.format_error("Couldn't disable do-not-disturb yet")
                return "Okay — do-not-disturb is off."

            return "What quiet hours should I use? Example: 'quiet hours 10pm-7am'."

        # Weekly digest schedule (e.g. "weekly digest monday 8pm")
        if "weekly digest" in message_lower:
            from core.onboarding import parse_hour_0_23
            day_map = {
                "monday": 0,
                "mon": 0,
                "tuesday": 1,
                "tue": 1,
                "wednesday": 2,
                "wed": 2,
                "thursday": 3,
                "thu": 3,
                "friday": 4,
                "fri": 4,
                "saturday": 5,
                "sat": 5,
                "sunday": 6,
                "sun": 6,
            }
            wd = None
            for k, v in day_map.items():
                if re.search(rf"\\b{k}\\b", message_lower):
                    wd = v
                    break
            wh = parse_hour_0_23(message_lower)
            if wd is not None and wh is not None:
                try:
                    self.user_prefs_repo.update(user_id, {"weekly_digest_day": wd, "weekly_digest_hour": int(wh)})
                except Exception as e:
                    print(f"Error updating weekly digest schedule: {e}")
                    return self.formatter.format_error("Couldn't update weekly digest settings yet")
                return f"Perfect — weekly digest set for day {wd} at {int(wh):02d}:00 (local time)."
            return "When do you want it? Example: 'weekly digest Monday 8pm'."

        # Default daily goals (water + macros)
        if "goal" in message_lower and any(k in message_lower for k in ["water", "calorie", "calories", "protein", "carb", "fat", "macros"]):
            updates: Dict[str, Any] = {}

            # Water goal like "3L" or "3000ml" or "100 oz"
            m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*(l|liter|litre|liters|litres)\\b", message_lower)
            if m:
                updates["default_water_goal_ml"] = int(float(m.group(1)) * 1000)
            m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*ml\\b", message_lower)
            if m:
                updates["default_water_goal_ml"] = int(float(m.group(1)))
            m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*oz\\b", message_lower)
            if m:
                updates["default_water_goal_ml"] = int(float(m.group(1)) * 29.5735)

            def find_g(field: str) -> Optional[int]:
                mm = re.search(rf"(\\d+(?:\\.\\d+)?)\\s*g\\s*(?:{field})\\b", message_lower)
                if mm:
                    return int(float(mm.group(1)))
                return None

            # calories like "2000 cal"
            m = re.search(r"(\\d{3,5})\\s*(cal|cals|calories)\\b", message_lower)
            if m:
                updates["default_calories_goal"] = int(m.group(1))

            p = find_g("protein|p")
            if p is not None:
                updates["default_protein_goal"] = p
            c = find_g("carbs|carb|c")
            if c is not None:
                updates["default_carbs_goal"] = c
            f = find_g("fat|f")
            if f is not None:
                updates["default_fat_goal"] = f

            if updates:
                try:
                    self.user_prefs_repo.update(user_id, updates)
                except Exception as e:
                    print(f"Error updating goals: {e}")
                    return self.formatter.format_error("Couldn't update goals yet")

                return "Locked in — updated your daily goals. You can tweak them anytime."

        return None
