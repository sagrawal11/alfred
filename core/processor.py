"""
Message Processor
Main message processing engine that coordinates NLP, handlers, and responses
"""

from typing import Dict, Optional, Any
from datetime import datetime

from nlp import (
    GeminiClient, IntentClassifier, EntityExtractor,
    Parser, PatternMatcher, DatabaseLoader
)
from data import (
    UserRepository, KnowledgeRepository
)
from core.context import ConversationContext
from core.session import SessionManager
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
        self.gemini_client = GeminiClient()
        self.db_loader = DatabaseLoader()
        self.intent_classifier = IntentClassifier(self.gemini_client)
        self.entity_extractor = EntityExtractor(self.gemini_client)
        self.parser = Parser(self.gemini_client, self.db_loader)
        
        # Initialize repositories
        self.user_repo = UserRepository(supabase)
        self.knowledge_repo = KnowledgeRepository(supabase)
        
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
    
    def process_message(self, message: str, phone_number: str) -> str:
        """
        Process an incoming message
        
        Args:
            message: Message text
            phone_number: Sender's phone number (E.164 format)
            
        Returns:
            Response text
        """
        try:
            # Get or create user
            user = self.user_repo.get_by_phone(phone_number)
            if not user:
                # Create new user
                user = self.user_repo.create_user(phone_number=phone_number)
            
            user_id = user['id']
            
            # Get session
            session = self.session_manager.get_session(user_id)
            
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
