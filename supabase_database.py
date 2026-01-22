#!/usr/bin/env python3
"""
Supabase Database Manager
Replaces CSV files with Supabase PostgreSQL database for persistent storage
"""

from datetime import datetime, date, time
from typing import List, Dict, Optional
from supabase import create_client, Client


class SupabaseDatabase:
    """Manages data storage using Supabase PostgreSQL database"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase database
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key or anon key
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    # Food logs methods
    def insert_food_log(self, food_name: str, calories: float, protein: float, 
                       carbs: float, fat: float, restaurant: Optional[str] = None,
                       portion_multiplier: float = 1.0, phone_number: Optional[str] = None) -> int:
        """Insert a food log entry"""
        data = {
            'food_name': food_name,
            'calories': float(calories),
            'protein': float(protein),
            'carbs': float(carbs),
            'fat': float(fat),
            'restaurant': restaurant,
            'portion_multiplier': float(portion_multiplier)
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        # If RLS requires it, we'll need to add the column to the database schema first
        result = self.supabase.table('food_logs').insert(data).execute()
        return result.data[0]['id']
    
    def get_food_logs(self, date: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Get food logs, optionally filtered by date or date range
        
        Args:
            date: Single date to filter by (YYYY-MM-DD) - takes precedence over start_date/end_date
            start_date: Start date for range filtering (YYYY-MM-DD)
            end_date: End date for range filtering (YYYY-MM-DD)
        """
        query = self.supabase.table('food_logs').select('*')
        
        if date:
            # Filter by single date (YYYY-MM-DD)
            start = f"{date}T00:00:00"
            end = f"{date}T23:59:59"
            query = query.gte('timestamp', start).lte('timestamp', end)
        elif start_date or end_date:
            # Filter by date range
            if start_date:
                start = f"{start_date}T00:00:00"
                query = query.gte('timestamp', start)
            if end_date:
                end = f"{end_date}T23:59:59"
                query = query.lte('timestamp', end)
        
        query = query.order('timestamp', desc=True)
        result = query.execute()
        return result.data if result.data else []
    
    # Water logs methods
    def insert_water_log(self, amount_ml: float, amount_oz: Optional[float] = None, phone_number: Optional[str] = None) -> int:
        """Insert a water log entry"""
        if amount_oz is None:
            amount_oz = amount_ml / 29.5735
        
        data = {
            'amount_ml': float(amount_ml),
            'amount_oz': float(amount_oz)
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('water_logs').insert(data).execute()
        return result.data[0]['id']
    
    def get_water_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get water logs, optionally filtered by date"""
        query = self.supabase.table('water_logs').select('*')
        
        if date:
            start_date = f"{date}T00:00:00"
            end_date = f"{date}T23:59:59"
            query = query.gte('timestamp', start_date).lte('timestamp', end_date)
        
        query = query.order('timestamp', desc=True)
        result = query.execute()
        return result.data if result.data else []
    
    # Gym logs methods
    def insert_gym_log(self, exercise: str, sets: Optional[int] = None,
                      reps: Optional[int] = None, weight: Optional[float] = None,
                      notes: Optional[str] = None, phone_number: Optional[str] = None) -> int:
        """Insert a gym log entry"""
        data = {
            'exercise': exercise,
            'sets': sets,
            'reps': reps,
            'weight': float(weight) if weight is not None else None,
            'notes': notes
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('gym_logs').insert(data).execute()
        return result.data[0]['id']
    
    def get_gym_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get gym logs, optionally filtered by date"""
        query = self.supabase.table('gym_logs').select('*')
        
        if date:
            start_date = f"{date}T00:00:00"
            end_date = f"{date}T23:59:59"
            query = query.gte('timestamp', start_date).lte('timestamp', end_date)
        
        query = query.order('timestamp', desc=True)
        result = query.execute()
        return result.data if result.data else []
    
    # Reminders and todos methods
    def insert_reminder_todo(self, type: str, content: str, 
                            due_date: Optional[datetime] = None,
                            completed: bool = False, phone_number: Optional[str] = None) -> int:
        """Insert a reminder or todo entry"""
        data = {
            'type': type,
            'content': content,
            'due_date': due_date.isoformat() if due_date else None,
            'completed': completed
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('reminders_todos').insert(data).execute()
        return result.data[0]['id']
    
    def get_reminders_todos(self, type: Optional[str] = None, 
                           completed: Optional[bool] = None,
                           due_before: Optional[datetime] = None) -> List[Dict]:
        """Get reminders/todos with optional filters"""
        query = self.supabase.table('reminders_todos').select('*')
        
        if type:
            query = query.eq('type', type)
        
        if completed is not None:
            query = query.eq('completed', completed)
        
        if due_before:
            query = query.lte('due_date', due_before.isoformat())
        
        query = query.order('timestamp', desc=True)
        result = query.execute()
        return result.data if result.data else []
    
    def update_reminder_todo(self, item_id: int, completed: bool = True, sent_at: Optional[str] = None):
        """Update a reminder/todo to mark as completed or update sent status"""
        update_data = {}
        
        if completed is not None:
            update_data['completed'] = completed
            if completed:
                update_data['completed_at'] = datetime.now().isoformat()
        
        if sent_at is not None:
            update_data['sent_at'] = sent_at
        
        if update_data:
            self.supabase.table('reminders_todos').update(update_data).eq('id', item_id).execute()
    
    def mark_follow_up_sent(self, item_id: int):
        """Mark that a follow-up has been sent for a reminder"""
        self.supabase.table('reminders_todos').update({'follow_up_sent': True}).eq('id', item_id).execute()
    
    def mark_decay_check_sent(self, item_id: int):
        """Mark that a decay check has been sent for a todo"""
        self.supabase.table('reminders_todos').update({'decay_check_sent': True}).eq('id', item_id).execute()
    
    def delete_water_log(self, water_id: int) -> bool:
        """Delete a water log by ID"""
        result = self.supabase.table('water_logs').delete().eq('id', water_id).execute()
        return result.data is not None and len(result.data) > 0
    
    def delete_food_log(self, food_id: int) -> bool:
        """Delete a food log by ID"""
        result = self.supabase.table('food_logs').delete().eq('id', food_id).execute()
        return result.data is not None and len(result.data) > 0
    
    def delete_gym_log(self, gym_id: int) -> bool:
        """Delete a gym log by ID"""
        result = self.supabase.table('gym_logs').delete().eq('id', gym_id).execute()
        return result.data is not None and len(result.data) > 0
    
    def delete_reminder_todo(self, item_id: int) -> bool:
        """Delete a reminder or todo by ID"""
        result = self.supabase.table('reminders_todos').delete().eq('id', item_id).execute()
        return result.data is not None and len(result.data) > 0
    
    def update_reminder_due_date(self, item_id: int, new_due_date: datetime):
        """Update a reminder's due date and reset sent flags"""
        update_data = {
            'due_date': new_due_date.isoformat(),
            'sent_at': None,
            'follow_up_sent': False
        }
        self.supabase.table('reminders_todos').update(update_data).eq('id', item_id).execute()
    
    def delete_old_logs(self, before_date: str):
        """Delete logs older than specified date (YYYY-MM-DD)"""
        cutoff = f"{before_date}T00:00:00"
        
        # Delete from each table
        self.supabase.table('food_logs').delete().lt('timestamp', cutoff).execute()
        self.supabase.table('water_logs').delete().lt('timestamp', cutoff).execute()
        self.supabase.table('gym_logs').delete().lt('timestamp', cutoff).execute()
        self.supabase.table('reminders_todos').delete().lt('timestamp', cutoff).execute()
    
    def get_stats(self) -> Dict[str, int]:
        """Get counts for all log types"""
        food_count = len(self.supabase.table('food_logs').select('id', count='exact').execute().data or [])
        water_count = len(self.supabase.table('water_logs').select('id', count='exact').execute().data or [])
        gym_count = len(self.supabase.table('gym_logs').select('id', count='exact').execute().data or [])
        reminder_count = len(self.supabase.table('reminders_todos').select('id', count='exact').execute().data or [])
        
        return {
            'food_logs': food_count,
            'water_logs': water_count,
            'gym_logs': gym_count,
            'reminders_todos': reminder_count
        }
    
    # Quote tracking methods
    def get_used_quotes(self) -> List[str]:
        """Get list of all quotes that have been used"""
        result = self.supabase.table('used_quotes').select('quote').execute()
        return [row['quote'] for row in result.data] if result.data else []
    
    def add_used_quote(self, quote: str, author: str = ''):
        """Record a quote as used"""
        today = datetime.now().date().isoformat()
        data = {
            'date': today,
            'quote': quote,
            'author': author
        }
        # Use upsert to handle duplicate key gracefully
        self.supabase.table('used_quotes').upsert(data, on_conflict='date,quote').execute()
    
    def get_todays_quote(self) -> Optional[Dict]:
        """Get today's quote if one was already fetched"""
        today = datetime.now().date().isoformat()
        result = self.supabase.table('used_quotes').select('*').eq('date', today).execute()
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return {
                'quote': row.get('quote', ''),
                'author': row.get('author', '')
            }
        return None
    
    # Water goals methods
    def get_water_goal(self, date: str, default_ml: float = 4000.0) -> float:
        """Get water goal for a specific date (YYYY-MM-DD), returns default if not set"""
        result = self.supabase.table('water_goals').select('goal_ml').eq('date', date).execute()
        if result.data and len(result.data) > 0:
            return float(result.data[0]['goal_ml'])
        return default_ml
    
    def set_water_goal(self, date: str, goal_ml: float):
        """Set water goal for a specific date (YYYY-MM-DD)"""
        data = {
            'date': date,
            'goal_ml': float(goal_ml)
        }
        # Use upsert to update if exists, insert if not
        self.supabase.table('water_goals').upsert(data, on_conflict='date').execute()
    
    def get_todays_water_total(self, date: Optional[str] = None) -> float:
        """Get total water logged for a specific date (defaults to today)"""
        if date is None:
            date = datetime.now().date().isoformat()
        
        water_logs = self.get_water_logs(date)
        total_ml = 0.0
        for log in water_logs:
            amount_ml = log.get('amount_ml')
            if amount_ml:
                try:
                    total_ml += float(amount_ml)
                except (ValueError, TypeError):
                    pass
        return total_ml
    
    def get_todays_food_totals(self, date: Optional[str] = None) -> Dict[str, float]:
        """Get total calories and macros for a specific date (defaults to today)"""
        if date is None:
            date = datetime.now().date().isoformat()
        
        food_logs = self.get_food_logs(date)
        totals = {
            'calories': 0.0,
            'protein': 0.0,
            'carbs': 0.0,
            'fat': 0.0
        }
        
        for log in food_logs:
            for key in totals.keys():
                value = log.get(key)
                if value:
                    try:
                        totals[key] += float(value)
                    except (ValueError, TypeError):
                        pass
        
        return totals
    
    # Sleep logs methods
    def insert_sleep_log(self, date: str, sleep_time: str, wake_time: str, duration_hours: float, phone_number: Optional[str] = None) -> int:
        """Insert a sleep log entry"""
        data = {
            'date': date,
            'sleep_time': sleep_time,
            'wake_time': wake_time,
            'duration_hours': float(duration_hours)
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('sleep_logs').insert(data).execute()
        return result.data[0]['id']
    
    def get_sleep_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get sleep logs, optionally filtered by date"""
        query = self.supabase.table('sleep_logs').select('*')
        
        if date:
            query = query.eq('date', date)
        
        query = query.order('date', desc=True)
        result = query.execute()
        return result.data if result.data else []
    
    def get_latest_sleep(self) -> Optional[Dict]:
        """Get the most recent sleep log"""
        result = self.supabase.table('sleep_logs').select('*').order('date', desc=True).order('sleep_time', desc=True).limit(1).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    # Facts (information recall) methods
    def insert_fact(self, key: str, value: str, context: Optional[str] = None, phone_number: Optional[str] = None) -> int:
        """Insert a fact/information entry"""
        data = {
            'key': key,
            'value': value,
            'context': context
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('facts').insert(data).execute()
        return result.data[0]['id']
    
    def get_all_facts(self) -> List[Dict]:
        """Get all facts"""
        result = self.supabase.table('facts').select('*').order('timestamp', desc=True).execute()
        return result.data if result.data else []
    
    def search_facts(self, query: str) -> List[Dict]:
        """Search facts by key or value (case-insensitive partial match)"""
        query_lower = query.lower()
        
        # Supabase doesn't have built-in case-insensitive search, so we'll fetch all and filter
        # For better performance with large datasets, consider using PostgreSQL full-text search
        all_facts = self.get_all_facts()
        
        matches = []
        for fact in all_facts:
            key = fact.get('key', '').lower()
            value = fact.get('value', '').lower()
            
            if query_lower in key or query_lower in value:
                matches.append(fact)
        
        return matches
    
    def get_fact(self, fact_id: int) -> Optional[Dict]:
        """Get a specific fact by ID"""
        result = self.supabase.table('facts').select('*').eq('id', fact_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    def delete_fact(self, fact_id: Optional[int] = None, key: Optional[str] = None) -> bool:
        """Delete a fact by ID or key"""
        if fact_id is not None:
            result = self.supabase.table('facts').delete().eq('id', fact_id).execute()
            return result.data is not None and len(result.data) > 0
        elif key is not None:
            result = self.supabase.table('facts').delete().eq('key', key).execute()
            return result.data is not None and len(result.data) > 0
        return False
    
    # Assignments methods
    def insert_assignment(self, class_name: str, assignment_name: str, 
                         due_date: datetime, notes: Optional[str] = None,
                         completed: bool = False, phone_number: Optional[str] = None) -> int:
        """Insert an assignment entry"""
        data = {
            'class_name': class_name,
            'assignment_name': assignment_name,
            'due_date': due_date.isoformat(),
            'notes': notes,
            'completed': completed
        }
        # Note: phone_number column doesn't exist in schema, so we don't include it
        result = self.supabase.table('assignments').insert(data).execute()
        return result.data[0]['id']
    
    def get_assignments(self, class_name: Optional[str] = None,
                       completed: Optional[bool] = None,
                       due_before: Optional[datetime] = None,
                       due_after: Optional[datetime] = None) -> List[Dict]:
        """Get assignments with optional filters"""
        query = self.supabase.table('assignments').select('*')
        
        if class_name:
            query = query.eq('class_name', class_name)
        
        if completed is not None:
            query = query.eq('completed', completed)
        
        if due_before:
            query = query.lte('due_date', due_before.isoformat())
        
        if due_after:
            query = query.gte('due_date', due_after.isoformat())
        
        query = query.order('due_date', desc=False)  # Order by due date ascending (earliest first)
        result = query.execute()
        return result.data if result.data else []
    
    def update_assignment(self, assignment_id: int, completed: Optional[bool] = None,
                         due_date: Optional[datetime] = None,
                         notes: Optional[str] = None):
        """Update an assignment"""
        update_data = {}
        
        if completed is not None:
            update_data['completed'] = completed
            if completed:
                update_data['completed_at'] = datetime.now().isoformat()
        
        if due_date is not None:
            update_data['due_date'] = due_date.isoformat()
        
        if notes is not None:
            update_data['notes'] = notes
        
        if update_data:
            self.supabase.table('assignments').update(update_data).eq('id', assignment_id).execute()
    
    def delete_assignment(self, assignment_id: int) -> bool:
        """Delete an assignment by ID"""
        result = self.supabase.table('assignments').delete().eq('id', assignment_id).execute()
        return result.data is not None and len(result.data) > 0

