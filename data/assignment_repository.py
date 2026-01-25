"""
Assignment Repository
Handles all assignment operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import Client
from .base_repository import BaseRepository


class AssignmentRepository(BaseRepository):
    """Repository for assignments"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'assignments')
    
    def create_assignment(self, user_id: int, class_name: str, assignment_name: str,
                         due_date: datetime, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new assignment
        
        Args:
            user_id: User ID
            class_name: Class name
            assignment_name: Assignment name
            due_date: Due date
            notes: Additional notes (optional)
            
        Returns:
            Created assignment record
        """
        data = {
            'user_id': user_id,
            'class_name': class_name,
            'assignment_name': assignment_name,
            'due_date': due_date.isoformat(),
            'completed': False,
            'notes': notes
        }
        return self.create(data)
    
    def get_incomplete(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get incomplete assignments
        
        Args:
            user_id: User ID
            
        Returns:
            List of incomplete assignments
        """
        return self.filter(
            {'user_id': user_id, 'completed': False},
            order_by='due_date',
            order_desc=False
        )
    
    def get_by_date(self, user_id: int, date_str: str) -> List[Dict[str, Any]]:
        """
        Get assignments due on a specific date.
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of assignments due on that date
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
    
    def get_by_class(self, user_id: int, class_name: str) -> List[Dict[str, Any]]:
        """
        Get assignments for a specific class
        
        Args:
            user_id: User ID
            class_name: Class name
            
        Returns:
            List of assignments for that class
        """
        return self.filter(
            {'user_id': user_id, 'class_name': class_name},
            order_by='due_date',
            order_desc=False
        )
    
    def get_due_soon(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get assignments due within specified days
        
        Args:
            user_id: User ID
            days: Number of days ahead to look (default: 7)
            
        Returns:
            List of assignments due soon
        """
        from datetime import timedelta
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        
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
        Get overdue assignments
        
        Args:
            user_id: User ID
            
        Returns:
            List of overdue assignments
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
    
    def mark_completed(self, assignment_id: int):
        """Mark an assignment as completed"""
        self.update(assignment_id, {
            'completed': True,
            'completed_at': datetime.now().isoformat()
        })
