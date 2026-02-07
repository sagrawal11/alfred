"""
Gym Repository
Handles all gym/workout log operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client

from .base_repository import BaseRepository


class GymRepository(BaseRepository):
    """Repository for gym/workout logs"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'gym_logs')
    
    def create_gym_log(self, user_id: int, exercise: str, sets: Optional[int] = None,
                      reps: Optional[int] = None, weight: Optional[float] = None,
                      notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new gym log entry
        
        Args:
            user_id: User ID
            exercise: Exercise name
            sets: Number of sets (optional)
            reps: Number of reps (optional)
            weight: Weight in lbs/kg (optional)
            notes: Additional notes (optional)
            
        Returns:
            Created gym log record
        """
        data = {
            'user_id': user_id,
            'exercise': exercise,
            'sets': sets,
            'reps': reps,
            'weight': float(weight) if weight is not None else None,
            'notes': notes
        }
        return self.create(data)
    
    def get_by_date(self, user_id: int, date_str: str) -> List[Dict[str, Any]]:
        """
        Get gym logs for a specific date
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of gym logs for that date
        """
        # Query by date range
        # Supabase timestamps may or may not have timezone info
        # Use date string format that works with both: YYYY-MM-DDTHH:MM:SS
        start = f"{date_str}T00:00:00"
        end = f"{date_str}T23:59:59.999999"
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("timestamp", start)\
            .lte("timestamp", end)\
            .order("timestamp", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def get_by_exercise(self, user_id: int, exercise: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get gym logs for a specific exercise
        
        Args:
            user_id: User ID
            exercise: Exercise name
            limit: Maximum number of records to return
            
        Returns:
            List of gym logs for that exercise
        """
        query = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("exercise", exercise)\
            .order("timestamp", desc=True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    
    def get_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get gym logs for a date range
        
        Args:
            user_id: User ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of gym logs in the date range
        """
        start = f"{start_date}T00:00:00"
        end = f"{end_date}T23:59:59"
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("timestamp", start)\
            .lte("timestamp", end)\
            .order("timestamp", desc=True)\
            .execute()
        
        return result.data if result.data else []
