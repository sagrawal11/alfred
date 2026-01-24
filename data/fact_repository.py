"""
Fact Repository
Handles all fact/information recall operations
"""

from typing import Dict, List, Optional, Any
from supabase import Client
from .base_repository import BaseRepository


class FactRepository(BaseRepository):
    """Repository for facts (information recall)"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'facts')
    
    def create_fact(self, user_id: int, key: str, value: str,
                   context: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new fact
        
        Args:
            user_id: User ID
            key: Fact key (e.g., "wifi_password")
            value: Fact value (e.g., "duke-guest-2025")
            context: Context where fact is relevant (optional)
            
        Returns:
            Created fact record
        """
        data = {
            'user_id': user_id,
            'key': key,
            'value': value,
            'context': context
        }
        return self.create(data)
    
    def get_by_key(self, user_id: int, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a fact by key
        
        Args:
            user_id: User ID
            key: Fact key
            
        Returns:
            Fact record or None if not found
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("key", key)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def search_facts(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """
        Search facts by key or value
        
        Args:
            user_id: User ID
            query: Search query
            
        Returns:
            List of matching facts
        """
        # Search in key
        key_results = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .ilike("key", f"%{query}%")\
            .execute()
        
        # Search in value
        value_results = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .ilike("value", f"%{query}%")\
            .execute()
        
        # Combine and deduplicate
        facts = {}
        for fact in (key_results.data or []):
            facts[fact['id']] = fact
        for fact in (value_results.data or []):
            facts[fact['id']] = fact
        
        return list(facts.values())
    
    def get_all_facts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all facts for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of all facts
        """
        return self.get_by_user_id(user_id, order_by='key', order_desc=False)
