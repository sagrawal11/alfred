"""
Conversation Context
Manages conversation state and context for better responses
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from typing import Optional
from data import (
    FoodRepository, WaterRepository, GymRepository,
    TodoRepository, SleepRepository, AssignmentRepository
)


class ConversationContext:
    """Manages conversation context for personalized responses"""
    
    def __init__(self, user_id: int, food_repo: FoodRepository, water_repo: WaterRepository,
                 gym_repo: GymRepository, todo_repo: TodoRepository,
                 sleep_repo: Optional[SleepRepository] = None, 
                 assignment_repo: Optional[AssignmentRepository] = None):
        """
        Initialize conversation context
        
        Args:
            user_id: User ID
            food_repo: Food repository
            water_repo: Water repository
            gym_repo: Gym repository
            todo_repo: Todo repository
            sleep_repo: Sleep repository
            assignment_repo: Assignment repository
        """
        self.user_id = user_id
        self.food_repo = food_repo
        self.water_repo = water_repo
        self.gym_repo = gym_repo
        self.todo_repo = todo_repo
        self.sleep_repo = sleep_repo
        self.assignment_repo = assignment_repo
        
        # Cache for today's data
        self._today_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
    
    def get_today_summary(self) -> Dict[str, Any]:
        """
        Get summary of today's activities
        
        Returns:
            Dictionary with today's totals and counts
        """
        now = datetime.now()
        
        # Check cache
        if (self._today_cache and self._cache_timestamp and
            now - self._cache_timestamp < self._cache_ttl):
            return self._today_cache
        
        # Get today's date in UTC to match Supabase timestamps
        # Supabase stores timestamps in UTC, so we need to use UTC date for queries
        today_utc = datetime.now(timezone.utc).date()
        today_str = today_utc.isoformat()
        
        # Get today's totals
        food_logs = self.food_repo.get_by_date(self.user_id, today_str)
        water_logs = self.water_repo.get_by_date(self.user_id, today_str)
        gym_logs = self.gym_repo.get_by_date(self.user_id, today_str)
        todos = self.todo_repo.get_incomplete(self.user_id)
        if self.assignment_repo:
            assignments = self.assignment_repo.get_incomplete(self.user_id)
        else:
            assignments = []
        
        # Calculate totals
        total_calories = sum(log.get('calories', 0) * log.get('portion_multiplier', 1.0) 
                            for log in food_logs)
        total_protein = sum(log.get('protein', 0) * log.get('portion_multiplier', 1.0) 
                           for log in food_logs)
        total_water_ml = sum(log.get('amount_ml', 0) for log in water_logs)
        
        # Build summary
        summary = {
            'date': today_str,
            'food': {
                'count': len(food_logs),
                'calories': round(total_calories, 1),
                'protein': round(total_protein, 1)
            },
            'water': {
                'count': len(water_logs),
                'ml': total_water_ml,
                'liters': round(total_water_ml / 1000, 2)
            },
            'gym': {
                'count': len(gym_logs)
            },
            'todos': {
                'incomplete': len(todos),
                'overdue': len(self.todo_repo.get_overdue(self.user_id))
            },
            'assignments': {
                'incomplete': len(assignments),
                'due_soon': len(self.assignment_repo.get_due_soon(self.user_id, days=3)) if self.assignment_repo else 0
            }
        }
        
        # Update cache
        self._today_cache = summary
        self._cache_timestamp = now
        
        return summary
    
    def get_recent_activity(self, hours: int = 24) -> Dict[str, List]:
        """
        Get recent activity within specified hours
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with recent activities
        """
        since = datetime.now() - timedelta(hours=hours)
        since_str = since.isoformat()
        
        # Use get_by_date_range for better performance
        today = datetime.now().date()
        today_str = today.isoformat()
        
        # Get today's date in UTC
        today_utc = datetime.now(timezone.utc).date()
        today_str = today_utc.isoformat()
        
        # Get today's logs
        food_logs = self.food_repo.get_by_date(self.user_id, today_str)
        water_logs = self.water_repo.get_by_date(self.user_id, today_str)
        gym_logs = self.gym_repo.get_by_date(self.user_id, today_str)
        
        # Filter by timestamp if needed (for hours < 24)
        if hours < 24:
            # Parse since_str and compare (handle both timezone-aware and naive timestamps)
            try:
                since_dt = datetime.fromisoformat(since_str.replace('Z', '+00:00'))
            except:
                since_dt = datetime.fromisoformat(since_str)
            
            def parse_timestamp(ts_str):
                """Parse timestamp, handling both timezone-aware and naive formats"""
                try:
                    return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                except:
                    return datetime.fromisoformat(ts_str)
            
            food_logs = [log for log in food_logs 
                        if parse_timestamp(log['timestamp']) >= since_dt]
            water_logs = [log for log in water_logs 
                         if parse_timestamp(log['timestamp']) >= since_dt]
            gym_logs = [log for log in gym_logs 
                       if parse_timestamp(log['timestamp']) >= since_dt]
        
        return {
            'food': food_logs,
            'water': water_logs,
            'gym': gym_logs
        }
    
    def invalidate_cache(self):
        """Invalidate the cache (call after data changes)"""
        self._today_cache = None
        self._cache_timestamp = None
