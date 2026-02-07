"""
Learning Orchestrator
Coordinates the learning system components
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from data import KnowledgeRepository
from .association_learner import AssociationLearner
from .context_analyzer import ContextAnalyzer
from .pattern_extractor import PatternExtractor


class LearningOrchestrator:
    """Orchestrates the learning system"""
    
    def __init__(self, knowledge_repo: KnowledgeRepository):
        """
        Initialize learning orchestrator
        
        Args:
            knowledge_repo: KnowledgeRepository instance
        """
        self.pattern_extractor = PatternExtractor()
        self.association_learner = AssociationLearner(knowledge_repo)
        self.context_analyzer = ContextAnalyzer()
        self.knowledge_repo = knowledge_repo
    
    def process_message_for_learning(self, user_id: int, message: str,
                                     intent: str, entities: Dict,
                                     result: Optional[Dict] = None,
                                     user_response: Optional[str] = None) -> List[Dict]:
        """
        Process a message to extract and learn patterns
        
        Args:
            user_id: User ID
            message: User message
            intent: Classified intent
            entities: Extracted entities
            result: Processing result
            user_response: User's response (for corrections/confirmations)
            
        Returns:
            List of learned patterns
        """
        learned_patterns = []
        
        # Check for learning opportunity
        is_opportunity, opportunity_data = self.context_analyzer.detect_learning_opportunity(
            message, intent, entities, result, user_response
        )
        
        if not is_opportunity:
            return learned_patterns
        
        # Extract patterns based on opportunity type
        if opportunity_data['type'] == 'explicit_teaching':
            patterns = self.pattern_extractor.extract_explicit_teaching(
                message, intent, entities, result
            )
            
            # Learn each pattern
            for pattern in patterns:
                learned = self.association_learner.learn_pattern(
                    user_id=user_id,
                    pattern_term=pattern['pattern_term'],
                    pattern_type=pattern['pattern_type'],
                    associated_value=pattern['associated_value'],
                    context=pattern.get('context'),
                    initial_confidence=pattern.get('confidence', 0.5)
                )
                learned_patterns.append(learned)
        
        elif opportunity_data['type'] == 'correction':
            # Extract pattern from correction
            # User said something, system got it wrong, user corrected
            # Learn: original term → correct intent
            correction = opportunity_data.get('correction', '')
            original_message = opportunity_data.get('original_message', message)
            
            # Try to extract what the user meant
            # This is simplified - in practice, might need more sophisticated extraction
            patterns = self.pattern_extractor.extract_explicit_teaching(
                correction, intent, entities, result
            )
            
            for pattern in patterns:
                learned = self.association_learner.learn_pattern(
                    user_id=user_id,
                    pattern_term=pattern['pattern_term'],
                    pattern_type=pattern['pattern_type'],
                    associated_value=pattern['associated_value'],
                    context=f"Correction: {original_message} -> {correction}",
                    initial_confidence=0.7
                )
                learned_patterns.append(learned)
        
        elif opportunity_data['type'] == 'confirmation':
            # User confirmed system's interpretation - reinforce pattern
            original_message = opportunity_data.get('original_message', message)
            key_terms = self.pattern_extractor._extract_key_terms(original_message)
            
            for term in key_terms:
                if len(term) > 3:
                    learned = self.association_learner.reinforce_pattern(
                        user_id=user_id,
                        pattern_term=term,
                        pattern_type='intent',
                        associated_value=intent,
                        success=True
                    )
                    if learned:
                        learned_patterns.append(learned)
        
        elif opportunity_data['type'] == 'ambiguous_term':
            # Try to learn from ambiguous terms (lower confidence)
            terms = opportunity_data.get('terms', [])
            for term in terms:
                # Only learn if we have some context (intent or result)
                if intent and intent != 'unknown':
                    learned = self.association_learner.learn_pattern(
                        user_id=user_id,
                        pattern_term=term,
                        pattern_type='intent',
                        associated_value=intent,
                        context=message,
                        initial_confidence=0.4
                    )
                    learned_patterns.append(learned)
        
        return learned_patterns
    
    def apply_learned_patterns(self, user_id: int, message: str) -> Tuple[Optional[str], Dict]:
        """
        Apply learned patterns to enhance message processing
        
        Args:
            user_id: User ID
            message: User message
            
        Returns:
            Tuple of (suggested_intent, suggested_entities)
        """
        # Get high-confidence patterns
        patterns = self.knowledge_repo.get_high_confidence_patterns(user_id, min_confidence=0.6)
        
        message_lower = message.lower()
        words = set(message_lower.split())
        
        suggested_intent = None
        suggested_entities = {}
        
        # Check each pattern
        for pattern in patterns:
            pattern_term = pattern.get('pattern_term', '').lower()
            
            # Check if pattern term appears in message
            if pattern_term in message_lower or pattern_term in words:
                pattern_type = pattern.get('pattern_type')
                associated_value = pattern.get('associated_value')
                confidence = pattern.get('confidence', 0.5)
                
                if pattern_type == 'intent' and confidence > 0.6:
                    # Suggest intent if confidence is high enough
                    if not suggested_intent or confidence > 0.8:
                        suggested_intent = associated_value
                
                elif pattern_type == 'entity':
                    # Add to suggested entities
                    entity_key = associated_value
                    if entity_key not in suggested_entities:
                        suggested_entities[entity_key] = []
                    suggested_entities[entity_key].append({
                        'value': pattern_term,
                        'confidence': confidence
                    })
        
        return suggested_intent, suggested_entities
    
    def record_pattern_usage(self, user_id: int, pattern_term: str,
                            pattern_type: str, associated_value: str,
                            success: bool):
        """
        Record that a pattern was used and whether it was successful
        
        Args:
            user_id: User ID
            pattern_term: Pattern term that was used
            pattern_type: Pattern type
            associated_value: Associated value
            success: Whether pattern usage was successful
        """
        self.association_learner.reinforce_pattern(
            user_id, pattern_term, pattern_type, associated_value, success
        )
