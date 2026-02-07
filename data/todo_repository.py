"""
Todo Repository
Handles all todo and reminder operations
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from supabase import Client

from .base_repository import BaseRepository


class TodoRepository(BaseRepository):
    """Repository for todos and reminders"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'reminders_todos')
    
    def create_todo(self, user_id: int, content: str, due_date: Optional[datetime] = None,
                   type: str = 'todo') -> Dict[str, Any]:
        """
        Create a new todo or reminder
        
        Args:
            user_id: User ID
            content: Todo/reminder content
            due_date: Due date (optional)
            type: 'todo' or 'reminder' (default: 'todo')
            
        Returns:
            Created todo/reminder record
        """
        data = {
            'user_id': user_id,
            'type': type,
            'content': content,
            'due_date': due_date.isoformat() if due_date else None,
            'completed': False
        }
        return self.create(data)
    
    def get_incomplete(self, user_id: int, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get incomplete todos/reminders
        
        Args:
            user_id: User ID
            type: Filter by type ('todo' or 'reminder'), None for all
            
        Returns:
            List of incomplete todos/reminders
        """
        filters = {'user_id': user_id, 'completed': False}
        if type:
            filters['type'] = type
        
        return self.filter(filters, order_by='due_date', order_desc=False)
    
    def get_completed(self, user_id: int, type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get completed todos/reminders
        
        Args:
            user_id: User ID
            type: Filter by type ('todo' or 'reminder'), None for all
            limit: Maximum number of records to return
            
        Returns:
            List of completed todos/reminders
        """
        filters = {'user_id': user_id, 'completed': True}
        if type:
            filters['type'] = type
        
        return self.filter(filters, limit=limit, order_by='completed_at', order_desc=True)
    
    def get_due_soon(self, user_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get todos/reminders due within specified hours
        
        Args:
            user_id: User ID
            hours: Number of hours ahead to look (default: 24)
            
        Returns:
            List of todos/reminders due soon
        """
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("completed", False)\
            .lte("due_date", cutoff.isoformat())\
            .gte("due_date", now.isoformat())\
            .order("due_date", desc=False)\
            .execute()
        
        return result.data if result.data else []
    
    def get_overdue(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get overdue todos/reminders
        
        Args:
            user_id: User ID
            
        Returns:
            List of overdue todos/reminders
        """
        now = datetime.now()
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("completed", False)\
            .lt("due_date", now.isoformat())\
            .order("due_date", desc=False)\
            .execute()
        
        return result.data if result.data else []
    
    def mark_completed(self, item_id: int):
        """Mark a todo/reminder as completed"""
        self.update(item_id, {
            'completed': True,
            'completed_at': datetime.now().isoformat()
        })
    
    def mark_sent(self, item_id: int):
        """Mark that a reminder has been sent"""
        self.update(item_id, {'sent_at': datetime.now().isoformat()})
    
    def mark_follow_up_sent(self, item_id: int):
        """Mark that a follow-up has been sent"""
        self.update(item_id, {'follow_up_sent': True})
    
    def mark_decay_check_sent(self, item_id: int):
        """Mark that a decay check has been sent"""
        self.update(item_id, {'decay_check_sent': True})
    
    def update_due_date(self, item_id: int, new_due_date: datetime):
        """Update a todo/reminder's due date and reset sent flags"""
        self.update(item_id, {
            'due_date': new_due_date.isoformat(),
            'sent_at': None,
            'follow_up_sent': False
        })
    
    def get_by_date(self, user_id: int, date_str: str) -> List[Dict[str, Any]]:
        """
        Get todos/reminders due on a specific date.
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of todos/reminders due on that date
        """
        start = f"{date_str}T00:00:00"
        end = f"{date_str}T23:59:59.999999"
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("due_date", start)\
            .lte("due_date", end)\
            .order("due_date", desc=False)\
            .execute()
        return result.data if result.data else []

    def get_by_due_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get todos/reminders with due_date in the given range.

        Args:
            user_id: User ID
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            List of todos/reminders in the range
        """
        start = f"{start_date}T00:00:00"
        end = f"{end_date}T23:59:59.999999"
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("due_date", start)\
            .lte("due_date", end)\
            .order("due_date", desc=False)\
            .execute()
        return result.data if result.data else []
    
    def get_stale_todos(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get todos that haven't been touched in specified days
        
        Args:
            user_id: User ID
            days: Number of days to consider stale (default: 7)
            
        Returns:
            List of stale todos
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("type", 'todo')\
            .eq("completed", False)\
            .lt("timestamp", cutoff.isoformat())\
            .eq("decay_check_sent", False)\
            .order("timestamp", desc=False)\
            .execute()
        
        return result.data if result.data else []
