"""
Association Learner
Manages pattern associations and confidence scores
"""

from typing import Dict, List, Optional
from datetime import datetime
from data import KnowledgeRepository


class AssociationLearner:
    """Manages learning of associations between terms and intents/entities"""
    
    def __init__(self, knowledge_repo: KnowledgeRepository):
        """
        Initialize association learner
        
        Args:
            knowledge_repo: KnowledgeRepository instance
        """
        self.knowledge_repo = knowledge_repo
    
    def learn_pattern(self, user_id: int, pattern_term: str, pattern_type: str,
                     associated_value: str, context: Optional[str] = None,
                     initial_confidence: float = 0.5) -> Dict:
        """
        Learn a new pattern or update existing one
        
        Args:
            user_id: User ID
            pattern_term: Term to learn (e.g., "dhamaka")
            pattern_type: Type ('intent', 'entity', 'synonym')
            associated_value: Associated value (e.g., "gym_workout")
            context: Context where learned
            initial_confidence: Initial confidence score
            
        Returns:
            Created or updated pattern
        """
        # Check if pattern already exists
        existing = self.knowledge_repo.get_pattern(
            user_id, pattern_term, pattern_type, associated_value
        )
        
        if existing:
            # Update existing pattern (increase confidence)
            new_confidence = min(1.0, existing.get('confidence', 0.5) + 0.1)
            return self.knowledge_repo.update_pattern(
                existing['id'],
                confidence=new_confidence
            )
        else:
            # Create new pattern
            return self.knowledge_repo.create_pattern(
                user_id=user_id,
                pattern_term=pattern_term,
                pattern_type=pattern_type,
                associated_value=associated_value,
                context=context,
                confidence=initial_confidence
            )
    
    def reinforce_pattern(self, user_id: int, pattern_term: str, 
                         pattern_type: str, associated_value: str, 
                         success: bool = True):
        """
        Reinforce a pattern based on usage success
        
        Args:
            user_id: User ID
            pattern_term: Pattern term
            pattern_type: Pattern type
            associated_value: Associated value
            success: Whether pattern was used successfully
        """
        pattern = self.knowledge_repo.get_pattern(
            user_id, pattern_term, pattern_type, associated_value
        )
        
        if pattern:
            self.knowledge_repo.increment_usage(pattern['id'], success=success)
        else:
            # Create pattern if it doesn't exist (implicit learning)
            self.learn_pattern(
                user_id, pattern_term, pattern_type, associated_value,
                initial_confidence=0.4 if success else 0.2
            )
    
    def get_best_match(self, user_id: int, term: str, 
                      pattern_type: str = 'intent') -> Optional[Dict]:
        """
        Get best matching pattern for a term
        
        Args:
            user_id: User ID
            term: Term to match
            pattern_type: Pattern type to search for
            
        Returns:
            Best matching pattern (highest confidence) or None
        """
        patterns = self.knowledge_repo.get_patterns_by_term(user_id, term)
        
        # Filter by type and get highest confidence
        matching = [p for p in patterns if p.get('pattern_type') == pattern_type]
        
        if not matching:
            return None
        
        # Return highest confidence pattern
        return max(matching, key=lambda p: p.get('confidence', 0))
    
    def get_all_associations(self, user_id: int, term: str) -> List[Dict]:
        """
        Get all associations for a term
        
        Args:
            user_id: User ID
            term: Term to search for
            
        Returns:
            List of all patterns for that term
        """
        return self.knowledge_repo.get_patterns_by_term(user_id, term)
