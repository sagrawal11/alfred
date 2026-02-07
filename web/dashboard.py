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

    @staticmethod
    def _gym_workout_exercise_counts(entries: List[Dict[str, Any]]) -> tuple:
        """
        Workout = cluster of entries within 2h of each other.
        Exercise = unique exercise type (same name = 1 exercise).
        Returns (workout_count, exercise_count).
        """
        def _parse_ts(ts):
            if not ts:
                return None
            s = str(ts).replace('Z', '+00:00').replace(' ', 'T')[:19]
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None

        sorted_entries = sorted(
            [e for e in (entries or []) if _parse_ts(e.get('timestamp'))],
            key=lambda e: _parse_ts(e.get('timestamp'))
        )
        if not sorted_entries:
            return 0, 0
        clusters = 1
        last_ts = _parse_ts(sorted_entries[0].get('timestamp'))
        for e in sorted_entries[1:]:
            ts = _parse_ts(e.get('timestamp'))
            if ts and last_ts and (ts - last_ts).total_seconds() > 2 * 3600:
                clusters += 1
            if ts:
                last_ts = ts
        unique_exercises = len(set(
            (e.get('exercise') or '').strip() or 'Unknown'
            for e in sorted_entries
        ))
        return clusters, unique_exercises

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
            def _num(x, default: float = 0.0) -> float:
                if x is None or x == '':
                    return default
                try:
                    return float(x)
                except Exception:
                    return default

            # Parse date
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            date_iso = target_date.isoformat()
            
            # Get food logs
            food_logs = self.food_repo.get_by_date(user_id, date_iso)
            total_calories = sum(_num(log.get('calories')) for log in food_logs)
            total_protein = sum(_num(log.get('protein')) for log in food_logs)
            total_carbs = sum(_num(log.get('carbs')) for log in food_logs)
            total_fat = sum(_num(log.get('fat')) for log in food_logs)
            
            # Get water logs
            water_logs = self.water_repo.get_by_date(user_id, date_iso)
            total_water_ml = sum(_num(log.get('amount_ml')) for log in water_logs)
            total_water_liters = round(total_water_ml / 1000, 2)

            # User's bottle size (fallback 500ml for display)
            bottle_ml = 500
            try:
                u = self.supabase.table('users').select('water_bottle_ml').eq('id', user_id).limit(1).execute()
                if u.data and u.data[0].get('water_bottle_ml'):
                    bottle_ml = int(u.data[0].get('water_bottle_ml'))
            except Exception:
                bottle_ml = 500
            
            # Get gym logs (workout = 2h cluster, exercise = unique type)
            gym_logs = self.gym_repo.get_by_date(user_id, date_iso)
            workout_count, exercise_count = self._gym_workout_exercise_counts(gym_logs)

            # Get todos
            todos = self.todo_repo.get_by_date(user_id, date_iso)
            completed_todos = sum(1 for todo in todos if todo.get('completed', False))
            total_todos = len(todos)
            
            # Get sleep logs
            # SleepRepository.get_by_date returns a single record (dict) or None
            sleep_log = self.sleep_repo.get_by_date(user_id, date_iso)
            if isinstance(sleep_log, dict):
                total_sleep_hours = _num(sleep_log.get('duration_hours'))
                sleep_sessions = 1
            else:
                total_sleep_hours = 0.0
                sleep_sessions = 0
            
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
                    'bottles': round(total_water_ml / bottle_ml, 1) if bottle_ml else 0
                },
                'gym': {
                    'workout_count': workout_count,
                    'exercise_count': exercise_count,
                    'exercises': [log.get('exercise', 'Unknown') for log in gym_logs]
                },
                'todos': {
                    'completed': completed_todos,
                    'total': total_todos,
                    'completion_rate': round((completed_todos / total_todos * 100) if total_todos > 0 else 0, 1)
                },
                'sleep': {
                    'total_hours': round(total_sleep_hours, 1),
                    'sessions': sleep_sessions
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

    def get_series_bulk(self, user_id: int, start_date_str: str, end_date_str: str) -> Dict[str, Dict[str, Any]]:
        """
        Get per-day stats for a date range using bulk queries (one per data type).
        Returns dict[date_iso] = { food: {...}, water: {...}, gym: {...}, sleep: {...}, todos: {...} }
        for building trends series without N×get_date_stats.
        """
        def _num(x, default: float = 0.0) -> float:
            if x is None or x == '':
                return default
            try:
                return float(x)
            except Exception:
                return default

        def _date_key(ts: str) -> str:
            if not ts:
                return ''
            s = str(ts).replace('Z', '+00:00')[:10]
            return s if len(s) == 10 else ''

        try:
            start_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_d = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_iso = start_d.isoformat()
            end_iso = end_d.isoformat()

            food_logs = self.food_repo.get_by_date_range(user_id, start_iso, end_iso)
            water_logs = self.water_repo.get_by_date_range(user_id, start_iso, end_iso)
            gym_logs = self.gym_repo.get_by_date_range(user_id, start_iso, end_iso)
            sleep_logs = self.sleep_repo.get_by_date_range(user_id, start_iso, end_iso)
            todos = self.todo_repo.get_by_due_date_range(user_id, start_iso, end_iso)

            by_date: Dict[str, Dict[str, Any]] = {}
            for i in range((end_d - start_d).days + 1):
                d = (start_d + timedelta(days=i)).isoformat()
                by_date[d] = {
                    'food': {'total_calories': 0.0, 'total_protein': 0.0, 'total_carbs': 0.0, 'total_fat': 0.0},
                    'water': {'total_ml': 0.0},
                    'gym': {'workout_count': 0, 'exercise_count': 0, '_entries': []},
                    'sleep': {'total_hours': 0.0},
                    'todos': {'completed': 0, 'total': 0},
                }

            for log in (food_logs or []):
                d = _date_key(log.get('timestamp'))
                if d in by_date:
                    b = by_date[d]['food']
                    b['total_calories'] += _num(log.get('calories'))
                    b['total_protein'] += _num(log.get('protein'))
                    b['total_carbs'] += _num(log.get('carbs'))
                    b['total_fat'] += _num(log.get('fat'))

            for log in (water_logs or []):
                d = _date_key(log.get('timestamp'))
                if d in by_date:
                    by_date[d]['water']['total_ml'] += _num(log.get('amount_ml'))

            for log in (gym_logs or []):
                d = _date_key(log.get('timestamp'))
                if d in by_date:
                    by_date[d]['gym']['_entries'].append({
                        'timestamp': log.get('timestamp'),
                        'exercise': log.get('exercise'),
                    })

            for d in by_date:
                wc, ec = self._gym_workout_exercise_counts(by_date[d]['gym']['_entries'])
                by_date[d]['gym']['workout_count'] = wc
                by_date[d]['gym']['exercise_count'] = ec
                del by_date[d]['gym']['_entries']

            for log in (sleep_logs or []):
                d = str(log.get('date') or '')[:10]
                if d in by_date:
                    by_date[d]['sleep']['total_hours'] = _num(log.get('duration_hours'))

            for log in (todos or []):
                d = str(log.get('due_date') or '')[:10]
                if d in by_date:
                    by_date[d]['todos']['total'] += 1
                    if log.get('completed', False):
                        by_date[d]['todos']['completed'] += 1

            return by_date
        except Exception:
            return {}

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
        today_str = date.today().isoformat()
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
