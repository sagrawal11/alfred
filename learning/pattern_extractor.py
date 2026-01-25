"""
Pattern Extractor
Extracts patterns from user messages for learning
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class PatternExtractor:
    """Extracts patterns from user messages"""
    
    def __init__(self):
        """Initialize pattern extractor"""
        pass
    
    def extract_explicit_teaching(self, message: str, intent: str, 
                                 entities: Dict, result: Optional[Dict] = None) -> List[Dict]:
        """
        Extract patterns from explicit teaching statements
        
        Examples:
        - "I had dhamaka practice today, count it as a workout"
        - "dhamaka means workout"
        - "when I say dhamaka, log it as gym"
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            result: Processing result (if available)
            
        Returns:
            List of extracted patterns:
            [
                {
                    'pattern_term': 'dhamaka',
                    'pattern_type': 'intent',
                    'associated_value': 'gym_workout',
                    'context': 'practice',
                    'confidence': 0.8
                }
            ]
        """
        patterns = []
        message_lower = message.lower()
        
        # Pattern 1: "X means Y" or "X is Y"
        # Example: "dhamaka means workout" or "dhamaka is a workout"
        means_pattern = re.search(r'(\w+)\s+(?:means|is|equals?)\s+(?:a\s+)?(\w+)', message_lower)
        if means_pattern:
            term = means_pattern.group(1)
            value = means_pattern.group(2)
            intent_map = self._map_value_to_intent(value)
            if intent_map:
                patterns.append({
                    'pattern_term': term,
                    'pattern_type': 'intent',
                    'associated_value': intent_map,
                    'context': message,
                    'confidence': 0.9  # High confidence for explicit teaching
                })
        
        # Pattern 2: "count X as Y" or "log X as Y"
        # Example: "count dhamaka as workout" or "log dhamaka as gym"
        # Skip if it's "count it as" (handled by pattern 4)
        count_pattern = re.search(r'(?:count|log)\s+(\w+)\s+as\s+(?:a\s+)?(\w+)', message_lower)
        if count_pattern and count_pattern.group(1) != 'it':
            term = count_pattern.group(1)
            value = count_pattern.group(2)
            # Skip pronouns and common words
            skip_words = {'it', 'this', 'that', 'them', 'these', 'those'}
            if term not in skip_words:
                intent_map = self._map_value_to_intent(value)
                if intent_map:
                    patterns.append({
                        'pattern_term': term,
                        'pattern_type': 'intent',
                        'associated_value': intent_map,
                        'context': message,
                        'confidence': 0.9
                    })
        
        # Pattern 3: "when I say X, do Y"
        # Example: "when I say dhamaka, log it as workout"
        when_pattern = re.search(r'when\s+i\s+say\s+(\w+)[,\s]+(?:log|count|treat)\s+it\s+as\s+(?:a\s+)?(\w+)', message_lower)
        if when_pattern:
            term = when_pattern.group(1)
            value = when_pattern.group(2)
            intent_map = self._map_value_to_intent(value)
            if intent_map:
                patterns.append({
                    'pattern_term': term,
                    'pattern_type': 'intent',
                    'associated_value': intent_map,
                    'context': message,
                    'confidence': 0.9
                })
        
        # Pattern 4: "X, count it as Y" (comma-separated)
        # Example: "I had dhamaka practice today, count it as a workout"
        # Look for the pattern: [phrase], count it as [value]
        comma_pattern = re.search(r',\s*(?:count|log)\s+it\s+as\s+(?:a\s+)?(\w+)', message_lower)
        if comma_pattern:
            value = comma_pattern.group(1)
            intent_map = self._map_value_to_intent(value)
            if intent_map:
                # Extract the phrase before the comma (skip common words)
                before_comma = message_lower[:message_lower.rfind(',')]
                # Find the most significant word
                stop_words = {'i', 'had', 'have', 'has', 'a', 'an', 'the', 'today', 'yesterday', 
                            'tomorrow', 'this', 'that', 'practice', 'session', 'workout', 'exercise'}
                words = re.findall(r'\b\w+\b', before_comma)
                # Filter out stop words and common activity words
                significant_words = [w for w in words if w not in stop_words and len(w) > 3]
                if significant_words:
                    # Prefer less common words (shorter unique words over longer common ones)
                    # Sort by length descending, but prefer words that look like proper nouns/unique terms
                    # (words that don't end in common suffixes like -ing, -ed, -ly)
                    def word_score(word):
                        # Prefer words that don't look like common verbs/adjectives
                        if word.endswith(('ing', 'ed', 'ly', 'er', 'est')):
                            return len(word) - 2  # Penalize common suffixes
                        return len(word)
                    
                    term = max(significant_words, key=word_score)
                    patterns.append({
                        'pattern_term': term,
                        'pattern_type': 'intent',
                        'associated_value': intent_map,
                        'context': message,
                        'confidence': 0.85
                    })
        
        return patterns
    
    def extract_implicit_patterns(self, message: str, intent: str, 
                                 entities: Dict, result: Optional[Dict] = None) -> List[Dict]:
        """
        Extract patterns from implicit usage (user corrections, confirmations)
        
        Examples:
        - User says "dhamaka" → system misclassifies → user corrects → learn pattern
        - User says "dhamaka practice" → system correctly identifies as workout → reinforce
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            result: Processing result
            
        Returns:
            List of extracted patterns
        """
        patterns = []
        
        # Extract key terms from message
        words = self._extract_key_terms(message)
        
        # If we have a successful result, create patterns from key terms
        if result and intent:
            for word in words:
                if len(word) > 3:  # Ignore short words
                    patterns.append({
                        'pattern_term': word,
                        'pattern_type': 'intent',
                        'associated_value': intent,
                        'context': message,
                        'confidence': 0.6  # Lower confidence for implicit learning
                    })
        
        return patterns
    
    def _extract_key_terms(self, message: str) -> List[str]:
        """Extract key terms from message (nouns, important words)"""
        # Simple extraction: words that are likely important
        # Remove common stop words
        stop_words = {'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'can', 'could', 'may', 'might', 'must', 'to', 'for', 'of', 'in',
                     'on', 'at', 'by', 'with', 'from', 'as', 'it', 'this', 'that', 'these',
                     'those', 'and', 'or', 'but', 'if', 'then', 'when', 'where', 'how',
                     'what', 'who', 'why', 'just', 'now', 'today', 'yesterday', 'tomorrow'}
        
        # Extract words (simple word boundary split)
        words = re.findall(r'\b\w+\b', message.lower())
        
        # Filter out stop words and short words
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms
    
    def _map_value_to_intent(self, value: str) -> Optional[str]:
        """Map a user-provided value to an intent"""
        value_lower = value.lower()
        
        # Map common terms to intents
        intent_map = {
            'workout': 'gym_workout',
            'gym': 'gym_workout',
            'exercise': 'gym_workout',
            'food': 'food_logging',
            'meal': 'food_logging',
            'eat': 'food_logging',
            'water': 'water_logging',
            'drink': 'water_logging',
            'todo': 'todo_add',
            'task': 'todo_add',
            'reminder': 'reminder_set',
            'remind': 'reminder_set',
            'assignment': 'assignment_add',
            'homework': 'assignment_add',
        }
        
        return intent_map.get(value_lower)
