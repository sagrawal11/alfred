"""
Base Repository Pattern
Provides common CRUD operations for all repositories
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import Client


class BaseRepository:
    """Base repository class with common database operations"""
    
    def __init__(self, supabase_client: Client, table_name: str):
        """
        Initialize repository
        
        Args:
            supabase_client: Supabase client instance
            table_name: Name of the database table
        """
        self.client = supabase_client
        self.table_name = table_name
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record
        
        Args:
            data: Dictionary of field names and values
            
        Returns:
            Created record as dictionary
        """
        result = self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return result.data[0]
        raise Exception(f"Failed to create record in {self.table_name}")
    
    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID
        
        Args:
            record_id: Record ID
            
        Returns:
            Record as dictionary or None if not found
        """
        result = self.client.table(self.table_name).select("*").eq("id", record_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    def get_by_user_id(self, user_id: int, limit: Optional[int] = None, 
                       order_by: Optional[str] = None, 
                       order_desc: bool = True) -> List[Dict[str, Any]]:
        """
        Get all records for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Order descending (True) or ascending (False)
            
        Returns:
            List of records
        """
        query = self.client.table(self.table_name).select("*").eq("user_id", user_id)
        
        if order_by:
            query = query.order(order_by, desc=order_desc)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    
    def update(self, record_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a record
        
        Args:
            record_id: Record ID
            data: Dictionary of fields to update
            
        Returns:
            Updated record as dictionary or None if not found
        """
        # Add updated_at timestamp if not provided (only for tables that have this column)
        # Note: Not all tables have updated_at (e.g., users, food_logs, etc. don't)
        # Only add for tables that explicitly have updated_at column
        if "updated_at" not in data:
            tables_with_updated_at = ['user_knowledge', 'user_integrations', 'user_preferences']
            if self.table_name in tables_with_updated_at:
                data["updated_at"] = datetime.now().isoformat()
        
        result = self.client.table(self.table_name).update(data).eq("id", record_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    def delete(self, record_id: int) -> bool:
        """
        Delete a record
        
        Args:
            record_id: Record ID
            
        Returns:
            True if deleted, False otherwise
        """
        result = self.client.table(self.table_name).delete().eq("id", record_id).execute()
        return result.data is not None
    
    def delete_by_user_id(self, user_id: int) -> int:
        """
        Delete all records for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of records deleted
        """
        result = self.client.table(self.table_name).delete().eq("user_id", user_id).execute()
        return len(result.data) if result.data else 0
    
    def count_by_user_id(self, user_id: int) -> int:
        """
        Count records for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of records
        """
        result = self.client.table(self.table_name).select("id", count="exact").eq("user_id", user_id).execute()
        return result.count if hasattr(result, 'count') else 0
    
    def exists(self, record_id: int) -> bool:
        """
        Check if a record exists
        
        Args:
            record_id: Record ID
            
        Returns:
            True if exists, False otherwise
        """
        result = self.get_by_id(record_id)
        return result is not None
    
    def filter(self, filters: Dict[str, Any], limit: Optional[int] = None,
               order_by: Optional[str] = None, order_desc: bool = True) -> List[Dict[str, Any]]:
        """
        Filter records by multiple criteria
        
        Args:
            filters: Dictionary of field names and values to filter by
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Order descending (True) or ascending (False)
            
        Returns:
            List of matching records
        """
        query = self.client.table(self.table_name).select("*")
        
        # Apply filters
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.in_(field, value)
            else:
                query = query.eq(field, value)
        
        if order_by:
            query = query.order(order_by, desc=order_desc)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    
    def get_all(self, limit: Optional[int] = None, 
                order_by: Optional[str] = None, 
                order_desc: bool = True) -> List[Dict[str, Any]]:
        """
        Get all records (use with caution - prefer get_by_user_id)
        
        Args:
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Order descending (True) or ascending (False)
            
        Returns:
            List of records
        """
        query = self.client.table(self.table_name).select("*")
        
        if order_by:
            query = query.order(order_by, desc=order_desc)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
