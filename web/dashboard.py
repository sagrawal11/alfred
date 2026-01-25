"""
Dashboard Data
Provides data for dashboard views
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta, date
from calendar import monthrange
from supabase import Client

from data import (
    FoodRepository, WaterRepository, GymRepository,
    TodoRepository, SleepRepository, AssignmentRepository
)
from config import Config


class DashboardData:
    """Provides dashboard data and statistics"""
    
    def __init__(self, supabase: Client):
        """
        Initialize dashboard data provider
        
        Args:
            supabase: Supabase client
        """
        self.supabase = supabase
        self.food_repo = FoodRepository(supabase)
        self.water_repo = WaterRepository(supabase)
        self.gym_repo = GymRepository(supabase)
        self.todo_repo = TodoRepository(supabase)
        self.sleep_repo = SleepRepository(supabase)
        self.assignment_repo = AssignmentRepository(supabase)
    
    def get_date_stats(self, user_id: int, date_str: str) -> Dict[str, Any]:
        """
        Get statistics for a specific date
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with stats for that date
        """
        try:
            # Parse date
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            date_iso = target_date.isoformat()
            
            # Get food logs
            food_logs = self.food_repo.get_by_date(user_id, date_iso)
            total_calories = sum(log.get('calories', 0) or 0 for log in food_logs)
            total_protein = sum(log.get('protein', 0) or 0 for log in food_logs)
            total_carbs = sum(log.get('carbs', 0) or 0 for log in food_logs)
            total_fat = sum(log.get('fat', 0) or 0 for log in food_logs)
            
            # Get water logs
            water_logs = self.water_repo.get_by_date(user_id, date_iso)
            total_water_ml = sum(log.get('amount_ml', 0) or 0 for log in water_logs)
            total_water_liters = round(total_water_ml / 1000, 2)
            
            # Get gym logs
            gym_logs = self.gym_repo.get_by_date(user_id, date_iso)
            workout_count = len(gym_logs)
            
            # Get todos
            todos = self.todo_repo.get_by_date(user_id, date_iso)
            completed_todos = sum(1 for todo in todos if todo.get('completed', False))
            total_todos = len(todos)
            
            # Get sleep logs
            sleep_logs = self.sleep_repo.get_by_date(user_id, date_iso)
            total_sleep_hours = sum(log.get('duration_hours', 0) or 0 for log in sleep_logs)
            
            # Get assignments
            assignments = self.assignment_repo.get_by_date(user_id, date_iso)
            completed_assignments = sum(1 for a in assignments if a.get('completed', False))
            total_assignments = len(assignments)
            
            return {
                'date': date_str,
                'food': {
                    'total_calories': total_calories,
                    'total_protein': round(total_protein, 1),
                    'total_carbs': round(total_carbs, 1),
                    'total_fat': round(total_fat, 1),
                    'meal_count': len(food_logs)
                },
                'water': {
                    'total_ml': total_water_ml,
                    'total_liters': total_water_liters,
                    'bottles': round(total_water_ml / 500, 1)  # Assuming 500ml bottles
                },
                'gym': {
                    'workout_count': workout_count,
                    'exercises': [log.get('exercise', 'Unknown') for log in gym_logs]
                },
                'todos': {
                    'completed': completed_todos,
                    'total': total_todos,
                    'completion_rate': round((completed_todos / total_todos * 100) if total_todos > 0 else 0, 1)
                },
                'sleep': {
                    'total_hours': round(total_sleep_hours, 1),
                    'sessions': len(sleep_logs)
                },
                'assignments': {
                    'completed': completed_assignments,
                    'total': total_assignments
                }
            }
        except Exception as e:
            return {
                'error': str(e),
                'date': date_str
            }
    
    def get_trends(self, user_id: int, end_date_str: str, days: int = 7) -> Dict[str, Any]:
        """
        Get trends for a date range
        
        Args:
            user_id: User ID
            end_date_str: End date in YYYY-MM-DD format
            days: Number of days to look back
            
        Returns:
            Dictionary with trend data
        """
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_date = end_date - timedelta(days=days - 1)
            
            # Collect data for each day
            daily_stats = []
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                date_iso = current_date.isoformat()
                
                stats = self.get_date_stats(user_id, date_iso)
                daily_stats.append(stats)
            
            # Calculate averages
            total_calories = sum(s.get('food', {}).get('total_calories', 0) for s in daily_stats)
            total_water_ml = sum(s.get('water', {}).get('total_ml', 0) for s in daily_stats)
            total_workouts = sum(s.get('gym', {}).get('workout_count', 0) for s in daily_stats)
            total_sleep_hours = sum(s.get('sleep', {}).get('total_hours', 0) for s in daily_stats)
            
            return {
                'start_date': start_date.isoformat(),
                'end_date': end_date_str,
                'days': days,
                'averages': {
                    'calories': round(total_calories / days, 0) if days > 0 else 0,
                    'water_liters': round(total_water_ml / 1000 / days, 2) if days > 0 else 0,
                    'workouts_per_week': round(total_workouts / days * 7, 1) if days > 0 else 0,
                    'sleep_hours': round(total_sleep_hours / days, 1) if days > 0 else 0
                },
                'totals': {
                    'calories': total_calories,
                    'water_liters': round(total_water_ml / 1000, 2),
                    'workouts': total_workouts,
                    'sleep_hours': round(total_sleep_hours, 1)
                },
                'daily_stats': daily_stats
            }
        except Exception as e:
            return {
                'error': str(e),
                'end_date': end_date_str,
                'days': days
            }
    
    def get_calendar_data(self, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Get calendar data for a month
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            Dictionary with calendar data
        """
        try:
            # Get first and last day of month
            first_day = date(year, month, 1)
            last_day_num = monthrange(year, month)[1]
            last_day = date(year, month, last_day_num)
            
            # Get all logs for the month
            start_date = first_day.isoformat()
            end_date = last_day.isoformat()
            
            # Get food logs
            food_logs = self.food_repo.get_by_date_range(user_id, start_date, end_date)
            
            # Get water logs
            water_logs = self.water_repo.get_by_date_range(user_id, start_date, end_date)
            
            # Get gym logs
            gym_logs = self.gym_repo.get_by_date_range(user_id, start_date, end_date)
            
            # Get todos (use get_incomplete and filter by date range)
            all_todos = self.todo_repo.get_incomplete(user_id)
            todos = [todo for todo in all_todos if start_date <= todo.get('due_date', '')[:10] <= end_date]
            
            # Organize by date
            calendar_data = {}
            for day in range(1, last_day_num + 1):
                date_obj = date(year, month, day)
                date_str = date_obj.isoformat()
                
                day_food = [log for log in food_logs if log.get('timestamp', '').startswith(date_str)]
                day_water = [log for log in water_logs if log.get('timestamp', '').startswith(date_str)]
                day_gym = [log for log in gym_logs if log.get('timestamp', '').startswith(date_str)]
                day_todos = [todo for todo in todos if todo.get('due_date', '').startswith(date_str)]
                
                calendar_data[date_str] = {
                    'has_food': len(day_food) > 0,
                    'has_water': len(day_water) > 0,
                    'has_gym': len(day_gym) > 0,
                    'has_todos': len(day_todos) > 0,
                    'activity_count': len(day_food) + len(day_water) + len(day_gym) + len(day_todos)
                }
            
            return {
                'year': year,
                'month': month,
                'first_day': start_date,
                'last_day': end_date,
                'calendar_data': calendar_data
            }
        except Exception as e:
            return {
                'error': str(e),
                'year': year,
                'month': month
            }
    
    def get_date_stats_for_frontend(self, user_id: int, date_str: str) -> Dict[str, Any]:
        """
        Get stats for a date in the format expected by the dashboard frontend.
        """
        s = self.get_date_stats(user_id, date_str)
        if s.get('error'):
            return s
        try:
            food_logs = self.food_repo.get_by_date(user_id, date_str)
            water_logs = self.water_repo.get_by_date(user_id, date_str)
            gym_logs = self.gym_repo.get_by_date(user_id, date_str)
            todos_all = self.todo_repo.get_by_date(user_id, date_str)
        except Exception as e:
            return {'error': str(e), 'date': date_str}
        
        todos_list = [t for t in todos_all if t.get('type') == 'todo']
        reminders_list = [t for t in todos_all if t.get('type') == 'reminder']
        todos_completed = [t for t in todos_list if t.get('completed')]
        todos_unfinished = [t for t in todos_list if not t.get('completed')]
        reminders_completed = [t for t in reminders_list if t.get('completed')]
        reminders_unfinished = [t for t in reminders_list if not t.get('completed')]
        
        assignments_all = self.assignment_repo.get_by_date(user_id, date_str)
        from datetime import date as date_type
        today_str = date_type.today().isoformat()
        if date_str < today_str:
            past_due = assignments_all
            due_today = []
        else:
            past_due = []
            due_today = assignments_all
        
        water_goal_ml = Config.DEFAULT_WATER_GOAL_ML
        return {
            'date': date_str,
            'food_logs': food_logs,
            'food_totals': {
                'calories': s['food']['total_calories'],
                'protein': s['food']['total_protein'],
                'carbs': s['food']['total_carbs'],
                'fat': s['food']['total_fat']
            },
            'water_logs': water_logs,
            'water_total_ml': s['water']['total_ml'],
            'water_goal_ml': water_goal_ml,
            'gym_logs': gym_logs,
            'todos': {'completed': todos_completed, 'unfinished': todos_unfinished},
            'reminders': {'completed': reminders_completed, 'unfinished': reminders_unfinished},
            'assignments': {'due_today': due_today, 'past_due': past_due}
        }
    
    def get_trends_for_frontend(self, user_id: int, end_date_str: str, days: int) -> Dict[str, Any]:
        """
        Get trends in the format expected by the dashboard frontend.
        """
        t = self.get_trends(user_id, end_date_str, days)
        if t.get('error'):
            return t
        try:
            from datetime import datetime, timedelta
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start = end - timedelta(days=days - 1)
            date_range = f"{start.isoformat()} to {end_date_str}"
        except Exception:
            date_range = f"{t.get('start_date', '')} to {t.get('end_date', '')}"
        
        av = t.get('averages', {})
        totals = t.get('totals', {})
        daily = t.get('daily_stats', [])
        gym_days = sum(1 for d in daily if (d.get('gym', {}) or {}).get('workout_count', 0) > 0)
        todo_total = sum((d.get('todos', {}) or {}).get('total', 0) for d in daily)
        todo_done = sum((d.get('todos', {}) or {}).get('completed', 0) for d in daily)
        todo_completion_rate = (todo_done / todo_total * 100) if todo_total else 0
        
        w_l = av.get('water_liters', 0) or 0
        water_avg_ml = int(float(w_l) * 1000) if isinstance(w_l, (int, float)) else 0
        return {
            'date_range': date_range,
            'water_avg_ml': water_avg_ml,
            'calories_avg': int(av.get('calories', 0) or 0),
            'gym_days': gym_days,
            'todo_completion_rate': round(todo_completion_rate, 1)
        }
