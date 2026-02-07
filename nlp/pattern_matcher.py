"""
Pattern Matcher
Applies learned patterns to user messages before NLP processing
"""

from typing import Any, Dict, List, Optional

from data import KnowledgeRepository


class PatternMatcher:
    """Applies learned patterns to enhance NLP processing"""
    
    def __init__(self, knowledge_repository: KnowledgeRepository):
        """
        Initialize pattern matcher
        
        Args:
            knowledge_repository: KnowledgeRepository instance
        """
        self.knowledge_repo = knowledge_repository
    
    def apply_patterns(self, message: str, user_id: int, intent: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply learned patterns to message
        
        Args:
            message: User message
            user_id: User ID
            intent: Current intent (if already classified)
            
        Returns:
            Dictionary with pattern matches:
            {
                'enhanced_message': str,  # Message with patterns applied
                'pattern_matches': List[Dict],  # List of matched patterns
                'suggested_intent': Optional[str],  # Intent suggested by patterns
                'suggested_entities': Dict  # Entities suggested by patterns
            }
        """
        message_lower = message.lower()
        words = set(message_lower.split())
        
        # Get high-confidence patterns for this user
        patterns = self.knowledge_repo.get_high_confidence_patterns(user_id, min_confidence=0.5)
        
        pattern_matches = []
        suggested_intent = intent
        suggested_entities = {}
        enhanced_message = message
        
        for pattern in patterns:
            pattern_term = pattern.get('pattern_term', '').lower()
            pattern_type = pattern.get('pattern_type', '')
            associated_value = pattern.get('associated_value', '')
            confidence = pattern.get('confidence', 0.5)
            
            # Check if pattern term appears in message
            if pattern_term in message_lower or any(word == pattern_term for word in words):
                pattern_matches.append({
                    'pattern': pattern,
                    'matched_term': pattern_term,
                    'confidence': confidence
                })
                
                # Apply pattern based on type
                if pattern_type == 'intent' and not intent:
                    # Suggest intent if not already classified
                    if confidence > 0.7:
                        suggested_intent = associated_value
                
                elif pattern_type == 'entity':
                    # Add entity to suggested entities
                    entity_key = associated_value
                    if entity_key not in suggested_entities:
                        suggested_entities[entity_key] = []
                    suggested_entities[entity_key].append({
                        'value': pattern_term,
                        'confidence': confidence
                    })
        
        # Sort matches by confidence
        pattern_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'enhanced_message': enhanced_message,
            'pattern_matches': pattern_matches,
            'suggested_intent': suggested_intent,
            'suggested_entities': suggested_entities
        }
    
    def find_similar_patterns(self, message: str, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Find similar patterns that might match (fuzzy matching)
        
        Args:
            message: User message
            user_id: User ID
            limit: Maximum number of patterns to return
            
        Returns:
            List of similar patterns
        """
        message_words = set(message.lower().split())
        
        # Get all patterns for user
        all_patterns = self.knowledge_repo.get_by_user_id(user_id)
        
        similar_patterns = []
        
        for pattern in all_patterns:
            pattern_term = pattern.get('pattern_term', '').lower()
            pattern_words = set(pattern_term.split())
            
            # Calculate similarity (simple word overlap)
            overlap = len(message_words & pattern_words)
            if overlap > 0:
                similarity = overlap / max(len(message_words), len(pattern_words))
                if similarity > 0.3:  # At least 30% overlap
                    similar_patterns.append({
                        'pattern': pattern,
                        'similarity': similarity
                    })
        
        # Sort by similarity and confidence
        similar_patterns.sort(key=lambda x: (x['similarity'], x['pattern'].get('confidence', 0)), reverse=True)
        
        return similar_patterns[:limit]
