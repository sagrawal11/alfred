"""
Notification Service
Handles gentle nudges and weekly digests
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from supabase import Client

from config import Config
from communication_service import CommunicationService
from data import UserRepository, WaterRepository, GymRepository, FoodRepository, TodoRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications (nudges, digests)"""
    
    def __init__(self, supabase: Client, config: Config, communication_service: CommunicationService):
        self.supabase = supabase
        self.config = config
        self.communication_service = communication_service
        self.user_repo = UserRepository(supabase)
        self.water_repo = WaterRepository(supabase)
        self.gym_repo = GymRepository(supabase)
        self.food_repo = FoodRepository(supabase)
        self.todo_repo = TodoRepository(supabase)
    
    def check_gentle_nudges(self):
        """Check and send gentle nudges for water and gym"""
        try:
            if not self.config.GENTLE_NUDGES_ENABLED:
                return
            
            current_time = datetime.now()
            
            # Get all users with phone numbers
            result = self.supabase.table('users')\
                .select("*")\
                .not_.is_('phone_number', 'null')\
                .execute()
            
            users = result.data if result.data else []
            
            for user in users:
                try:
                    user_id = user['id']
                    user_phone = user.get('phone_number')
                    
                    if not user_phone or user_phone.startswith('web-'):
                        continue  # Skip web-only users
                    
                    # Check water intake
                    self._check_water_nudge(user_id, user_phone, current_time)
                    
                    # Check gym activity
                    self._check_gym_nudge(user_id, user_phone, current_time)
                
                except Exception as e:
                    logger.error(f"Error checking nudges for user {user_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking gentle nudges: {e}")
    
    def _check_water_nudge(self, user_id: int, user_phone: str, current_time: datetime):
        """Check if user needs a water nudge"""
        try:
            # Get today's water intake
            today_str = current_time.date().isoformat()
            today_logs = self.water_repo.get_by_date(user_id, today_str)
            
            total_ml = sum(float(log.get('amount_ml', 0)) for log in today_logs)
            
            # Get goal (default from config)
            goal_ml = self.config.DEFAULT_WATER_GOAL_ML
            
            # Calculate expected intake at this time of day
            hour = current_time.hour
            expected_progress = hour / 16.0  # Assume 16-hour day (8am to midnight)
            expected_ml = goal_ml * expected_progress
            
            # If significantly behind (more than 20% behind expected)
            if total_ml < expected_ml * 0.8 and expected_ml > 500:
                bottles_behind = int((expected_ml - total_ml) / self.config.WATER_BOTTLE_SIZE_ML)
                message = f"You're about {bottles_behind} bottle{'s' if bottles_behind > 1 else ''} behind your usual pace today. Just a gentle reminder!"
                
                result = self.communication_service.send_response(message, user_phone)
                if result['success']:
                    logger.info(f"Water nudge sent to user {user_id}")
        
        except Exception as e:
            logger.debug(f"Error checking water nudge: {e}")
    
    def _check_gym_nudge(self, user_id: int, user_phone: str, current_time: datetime):
        """Check if user needs a gym nudge"""
        try:
            # Get last gym log
            result = self.supabase.table('gym_logs')\
                .select("*")\
                .eq('user_id', user_id)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if not result.data:
                # No gym logs at all - don't nudge (might be new user)
                return
            
            last_log = result.data[0]
            last_log_date_str = last_log.get('timestamp') or last_log.get('created_at')
            
            if not last_log_date_str:
                return
            
            try:
                last_log_date = datetime.fromisoformat(last_log_date_str.replace('Z', '+00:00'))
                if last_log_date.tzinfo is None:
                    last_log_date = last_log_date.replace(tzinfo=timedelta(hours=0))
                
                days_since = (current_time - last_log_date.replace(tzinfo=None)).days
                
                # Only nudge if it's been 2+ days
                if days_since >= 2:
                    message = f"It's been {days_since} days since your last workout - just a gentle reminder"
                    
                    result = self.communication_service.send_response(message, user_phone)
                    if result['success']:
                        logger.info(f"Gym nudge sent to user {user_id}")
            
            except Exception as e:
                logger.debug(f"Error parsing last gym date: {e}")
        
        except Exception as e:
            logger.debug(f"Error checking gym nudge: {e}")
    
    def send_weekly_digest(self):
        """Send weekly summary of behavior and progress"""
        try:
            if not self.config.WEEKLY_DIGEST_ENABLED:
                return
            
            today = datetime.now().date()
            
            # Calculate week boundaries (Monday to Sunday)
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Get all users with phone numbers
            result = self.supabase.table('users')\
                .select("*")\
                .not_.is_('phone_number', 'null')\
                .execute()
            
            users = result.data if result.data else []
            
            for user in users:
                try:
                    user_id = user['id']
                    user_phone = user.get('phone_number')
                    
                    if not user_phone or user_phone.startswith('web-'):
                        continue  # Skip web-only users
                    
                    # Get week's data
                    week_water = self._get_week_water(user_id, week_start, week_end)
                    week_food = self._get_week_food(user_id, week_start, week_end)
                    week_gym = self._get_week_gym(user_id, week_start, week_end)
                    week_todos = self._get_week_todos(user_id, week_start, week_end)
                    
                    # Calculate stats
                    total_water_ml = sum(float(log.get('amount_ml', 0)) for log in week_water)
                    avg_water_ml = total_water_ml / 7 if week_water else 0
                    
                    total_calories = sum(float(log.get('calories', 0)) for log in week_food)
                    avg_calories = total_calories / 7 if week_food else 0
                    
                    gym_days = len(set(log.get('timestamp', '')[:10] for log in week_gym if log.get('timestamp')))
                    
                    completed_todos = sum(1 for todo in week_todos if todo.get('completed', False))
                    total_todos = len(week_todos)
                    completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
                    
                    # Build digest message
                    message = "📊 Weekly Digest:\n\n"
                    message += f"💧 Water: {int(avg_water_ml)}mL/day avg\n"
                    message += f"🍽️ Food: {int(avg_calories)} cal/day avg\n"
                    message += f"💪 Gym: {gym_days} day{'s' if gym_days != 1 else ''}\n"
                    message += f"✅ Tasks: {completed_todos}/{total_todos} completed ({int(completion_rate)}%)"
                    
                    result = self.communication_service.send_response(message, user_phone)
                    if result['success']:
                        logger.info(f"Weekly digest sent to user {user_id}")
                
                except Exception as e:
                    logger.error(f"Error sending weekly digest to user {user_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error sending weekly digest: {e}")
    
    def _get_week_water(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get water logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.water_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_food(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get food logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.food_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_gym(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get gym logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.gym_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_todos(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get todos for the week"""
        # Get todos created or due during the week
        start_str = week_start.isoformat()
        end_str = (week_end + timedelta(days=1)).isoformat()
        
        result = self.supabase.table('reminders_todos')\
            .select("*")\
            .eq('user_id', user_id)\
            .gte('created_at', start_str)\
            .lte('created_at', end_str)\
            .execute()
        
        return result.data if result.data else []
