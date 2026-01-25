"""
Context Analyzer
Detects learning opportunities from user interactions
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ContextAnalyzer:
    """Analyzes context to detect learning opportunities"""
    
    def __init__(self):
        """Initialize context analyzer"""
        pass
    
    def detect_learning_opportunity(self, message: str, intent: str,
                                   entities: Dict, result: Optional[Dict],
                                   user_response: Optional[str] = None) -> Tuple[bool, Optional[Dict]]:
        """
        Detect if there's a learning opportunity
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            result: Processing result
            user_response: User's response (if correction/confirmation)
            
        Returns:
            Tuple of (is_opportunity, opportunity_data)
            opportunity_data: {
                'type': 'explicit_teaching' | 'correction' | 'confirmation',
                'pattern_term': str,
                'pattern_type': str,
                'associated_value': str,
                'confidence': float
            }
        """
        message_lower = message.lower()
        
        # Check for explicit teaching patterns
        # Match patterns like "X means Y", "count X as Y", "count it as Y", "log it as Y"
        teaching_patterns = [
            'means', 'is', 'equals',
            'count as', 'count it as',
            'log as', 'log it as',
            'when i say'
        ]
        if any(pattern in message_lower for pattern in teaching_patterns):
            return True, {
                'type': 'explicit_teaching',
                'message': message,
                'confidence': 0.9
            }
        
        # Check for corrections (user says something, system misclassifies, user corrects)
        if user_response:
            correction_keywords = ['no', 'wrong', 'not', 'actually', 'it was', 'that was']
            if any(keyword in user_response.lower() for keyword in correction_keywords):
                return True, {
                    'type': 'correction',
                    'original_message': message,
                    'correction': user_response,
                    'confidence': 0.7
                }
        
        # Check for confirmations (user confirms system's interpretation)
        if user_response:
            confirmation_keywords = ['yes', 'correct', 'right', 'that\'s it', 'exactly']
            if any(keyword in user_response.lower() for keyword in confirmation_keywords):
                return True, {
                    'type': 'confirmation',
                    'original_message': message,
                    'confirmation': user_response,
                    'confidence': 0.6
                }
        
        # Check for ambiguous terms that might need learning
        # If intent is 'unknown' but message has specific terms, might be learnable
        if intent == 'unknown':
            # Extract potential terms
            words = message_lower.split()
            # Filter out common words
            important_words = [w for w in words if len(w) > 4 and w.isalpha()]
            if important_words:
                return True, {
                    'type': 'ambiguous_term',
                    'terms': important_words,
                    'message': message,
                    'confidence': 0.4
                }
        
        return False, None
    
    def extract_context_features(self, message: str, intent: str,
                                entities: Dict, result: Optional[Dict]) -> Dict:
        """
        Extract contextual features for learning
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            result: Processing result
            
        Returns:
            Dictionary of contextual features
        """
        return {
            'message_length': len(message),
            'word_count': len(message.split()),
            'has_numbers': any(char.isdigit() for char in message),
            'has_time': 'time' in entities or 'times' in entities,
            'has_date': 'date' in entities or 'dates' in entities,
            'intent': intent,
            'entities_count': sum(len(v) if isinstance(v, list) else 1 for v in entities.values()),
            'result_success': result is not None
        }
