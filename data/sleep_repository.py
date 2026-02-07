"""
Sleep Repository
Handles all sleep log operations
"""

from datetime import date, time
from typing import Any, Dict, List, Optional

from supabase import Client

from .base_repository import BaseRepository


class SleepRepository(BaseRepository):
    """Repository for sleep logs"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'sleep_logs')
    
    def create_sleep_log(self, user_id: int, date_str: str, sleep_time: time,
                        wake_time: time, duration_hours: float) -> Dict[str, Any]:
        """
        Create a new sleep log entry
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            sleep_time: Sleep time
            wake_time: Wake time
            duration_hours: Sleep duration in hours
            
        Returns:
            Created sleep log record
        """
        data = {
            'user_id': user_id,
            'date': date_str,
            'sleep_time': sleep_time.strftime('%H:%M:%S'),
            'wake_time': wake_time.strftime('%H:%M:%S'),
            'duration_hours': float(duration_hours)
        }
        return self.create(data)
    
    def get_by_date(self, user_id: int, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Get sleep log for a specific date
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Sleep log record or None if not found
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("date", date_str)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def get_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get sleep logs for a date range
        
        Args:
            user_id: User ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of sleep logs in the date range
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("date", start_date)\
            .lte("date", end_date)\
            .order("date", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def get_average_duration(self, user_id: int, days: int = 7) -> float:
        """
        Get average sleep duration over specified days
        
        Args:
            user_id: User ID
            days: Number of days to average (default: 7)
            
        Returns:
            Average sleep duration in hours
        """
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        logs = self.get_by_date_range(user_id, start_date.isoformat(), end_date.isoformat())
        
        if not logs:
            return 0.0
        
        total = sum(float(log.get('duration_hours', 0)) for log in logs)
        return total / len(logs)
