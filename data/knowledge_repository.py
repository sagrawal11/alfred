"""
Knowledge Repository
Handles all user knowledge (learned patterns) operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import Client
from .base_repository import BaseRepository


class KnowledgeRepository(BaseRepository):
    """Repository for user knowledge (learned patterns)"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'user_knowledge')
    
    def create_pattern(self, user_id: int, pattern_term: str, pattern_type: str,
                      associated_value: str, context: Optional[str] = None,
                      category: Optional[str] = None, confidence: float = 0.5) -> Dict[str, Any]:
        """
        Create a new learned pattern
        
        Args:
            user_id: User ID
            pattern_term: The term/word to learn (e.g., "dhamaka")
            pattern_type: Type of pattern ('intent', 'entity', 'synonym')
            associated_value: What it's associated with (e.g., "gym_workout")
            context: Context where it was learned (optional)
            category: Category of pattern (optional)
            confidence: Initial confidence score (default: 0.5)
            
        Returns:
            Created pattern record
        """
        data = {
            'user_id': user_id,
            'pattern_term': pattern_term,
            'pattern_type': pattern_type,
            'associated_value': associated_value,
            'context': context,
            'category': category,
            'confidence': float(confidence),
            'usage_count': 1,
            'success_count': 0,
            'failure_count': 0
        }
        
        # Use upsert to handle duplicates
        try:
            return self.create(data)
        except Exception:
            # Pattern might already exist, try to update instead
            existing = self.get_pattern(user_id, pattern_term, pattern_type, associated_value)
            if existing:
                return self.update_pattern(existing['id'], confidence=confidence)
            raise
    
    def get_pattern(self, user_id: int, pattern_term: str, pattern_type: str,
                   associated_value: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern
        
        Args:
            user_id: User ID
            pattern_term: Pattern term
            pattern_type: Pattern type
            associated_value: Associated value
            
        Returns:
            Pattern record or None if not found
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("pattern_term", pattern_term)\
            .eq("pattern_type", pattern_type)\
            .eq("associated_value", associated_value)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def get_patterns_by_term(self, user_id: int, pattern_term: str) -> List[Dict[str, Any]]:
        """
        Get all patterns matching a term
        
        Args:
            user_id: User ID
            pattern_term: Pattern term to search for
            
        Returns:
            List of matching patterns
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("pattern_term", pattern_term)\
            .order("confidence", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def get_patterns_by_type(self, user_id: int, pattern_type: str,
                            min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """
        Get all patterns of a specific type
        
        Args:
            user_id: User ID
            pattern_type: Pattern type ('intent', 'entity', 'synonym')
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of patterns
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("pattern_type", pattern_type)\
            .gte("confidence", min_confidence)\
            .order("confidence", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def update_pattern(self, pattern_id: int, confidence: Optional[float] = None,
                     usage_count: Optional[int] = None, success_count: Optional[int] = None,
                     failure_count: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Update a pattern
        
        Args:
            pattern_id: Pattern ID
            confidence: New confidence score
            usage_count: New usage count
            success_count: New success count
            failure_count: New failure count
            
        Returns:
            Updated pattern record
        """
        update_data = {}
        
        if confidence is not None:
            update_data['confidence'] = float(confidence)
        
        if usage_count is not None:
            update_data['usage_count'] = usage_count
        
        if success_count is not None:
            update_data['success_count'] = success_count
        
        if failure_count is not None:
            update_data['failure_count'] = failure_count
        
        # Calculate effectiveness score
        pattern = self.get_by_id(pattern_id)
        if pattern:
            total = pattern.get('success_count', 0) + pattern.get('failure_count', 0)
            if total > 0:
                effectiveness = pattern.get('success_count', 0) / total
                update_data['effectiveness_score'] = effectiveness
        
        update_data['last_used'] = datetime.now().isoformat()
        
        return self.update(pattern_id, update_data)
    
    def increment_usage(self, pattern_id: int, success: bool = True):
        """
        Increment pattern usage and update confidence
        
        Args:
            pattern_id: Pattern ID
            success: Whether the pattern was used successfully
        """
        pattern = self.get_by_id(pattern_id)
        if not pattern:
            return
        
        usage_count = pattern.get('usage_count', 0) + 1
        success_count = pattern.get('success_count', 0)
        failure_count = pattern.get('failure_count', 0)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
        
        # Update confidence based on success rate
        total = success_count + failure_count
        if total > 0:
            confidence = success_count / total
        else:
            confidence = 0.5
        
        self.update_pattern(pattern_id, confidence=confidence, usage_count=usage_count,
                          success_count=success_count, failure_count=failure_count)
    
    def get_high_confidence_patterns(self, user_id: int, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        Get high-confidence patterns
        
        Args:
            user_id: User ID
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of high-confidence patterns
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("confidence", min_confidence)\
            .order("confidence", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def prune_low_confidence(self, user_id: int, min_confidence: float = 0.2):
        """
        Delete patterns with confidence below threshold
        
        Args:
            user_id: User ID
            min_confidence: Minimum confidence to keep
        """
        result = self.client.table(self.table_name)\
            .delete()\
            .eq("user_id", user_id)\
            .lt("confidence", min_confidence)\
            .execute()
        
        return len(result.data) if result.data else 0
