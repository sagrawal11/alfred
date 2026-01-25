"""
Base Handler
Abstract base class for all intent handlers
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from supabase import Client

from core.context import ConversationContext


class BaseHandler(ABC):
    """Base class for all intent handlers"""
    
    def __init__(self, supabase: Client, parser, formatter):
        """
        Initialize base handler
        
        Args:
            supabase: Supabase client
            parser: Parser instance
            formatter: ResponseFormatter instance
        """
        self.supabase = supabase
        self.parser = parser
        self.formatter = formatter
    
    @abstractmethod
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """
        Handle a message with the given intent
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            user_id: User ID
            context: Conversation context
            
        Returns:
            Response message or None
        """
        pass
    
    def handle_confirmation(self, message: str, user_id: int, 
                          pending: Dict) -> Optional[str]:
        """
        Handle a confirmation response
        
        Args:
            message: Confirmation message
            user_id: User ID
            pending: Pending confirmation data
            
        Returns:
            Response message or None
        """
        return None
    
    def validate_user(self, user_id: int) -> bool:
        """
        Validate that user exists and is active
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is valid
        """
        from data import UserRepository
        user_repo = UserRepository(self.supabase)
        user = user_repo.get_by_id(user_id)
        return user is not None and user.get('is_active', True)
