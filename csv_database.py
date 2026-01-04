#!/usr/bin/env python3
"""
CSV Database Manager
Replaces SQLite with CSV files for simpler data storage
"""

import os
import csv
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

class CSVDatabase:
    """Manages data storage using CSV files"""
    
    def __init__(self, data_dir: str):
        """Initialize CSV database
        
        Args:
            data_dir: Directory where CSV files will be stored
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # CSV file paths
        self.food_logs_file = os.path.join(data_dir, 'food_logs.csv')
        self.water_logs_file = os.path.join(data_dir, 'water_logs.csv')
        self.gym_logs_file = os.path.join(data_dir, 'gym_logs.csv')
        self.reminders_todos_file = os.path.join(data_dir, 'reminders_todos.csv')
        self.used_quotes_file = os.path.join(data_dir, 'used_quotes.csv')
        self.water_goals_file = os.path.join(data_dir, 'water_goals.csv')
        
        # Initialize CSV files with headers if they don't exist
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Create CSV files with headers if they don't exist"""
        # Food logs
        if not os.path.exists(self.food_logs_file):
            with open(self.food_logs_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'timestamp', 'food_name', 'calories', 'protein', 
                    'carbs', 'fat', 'restaurant', 'portion_multiplier'
                ])
        
        # Water logs
        if not os.path.exists(self.water_logs_file):
            with open(self.water_logs_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'timestamp', 'amount_ml', 'amount_oz'])
        
        # Gym logs
        if not os.path.exists(self.gym_logs_file):
            with open(self.gym_logs_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'timestamp', 'exercise', 'sets', 'reps', 'weight', 'notes'
                ])
        
        # Reminders and todos
        if not os.path.exists(self.reminders_todos_file):
            with open(self.reminders_todos_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'timestamp', 'type', 'content', 'due_date', 'completed', 'completed_at', 'sent_at', 'follow_up_sent', 'decay_check_sent'
                ])
        
        # Used quotes (to track which quotes have been shown)
        if not os.path.exists(self.used_quotes_file):
            with open(self.used_quotes_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'quote', 'author'])
        
        # Water goals (to track custom daily water goals)
        if not os.path.exists(self.water_goals_file):
            with open(self.water_goals_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'goal_ml'])
    
    def _get_next_id(self, csv_file: str) -> int:
        """Get the next ID for a CSV file"""
        if not os.path.exists(csv_file):
            return 1
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return 1
            max_id = max(int(row.get('id', 0)) for row in rows if row.get('id', '').isdigit())
            return max_id + 1
    
    def _read_csv(self, csv_file: str) -> List[Dict]:
        """Read all rows from a CSV file"""
        if not os.path.exists(csv_file):
            return []
        
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows
    
    def _write_csv(self, csv_file: str, rows: List[Dict], fieldnames: List[str]):
        """Write rows to a CSV file"""
        # Filter rows to only include expected fieldnames and ensure all fields exist
        filtered_rows = []
        for row in rows:
            filtered_row = {}
            for field in fieldnames:
                # Get value from row, defaulting to empty string if missing
                filtered_row[field] = row.get(field, '')
            filtered_rows.append(filtered_row)
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_rows)
    
    def _append_csv(self, csv_file: str, row: Dict, fieldnames: List[str]):
        """Append a row to a CSV file"""
        file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    
    # Food logs methods
    def insert_food_log(self, food_name: str, calories: float, protein: float, 
                       carbs: float, fat: float, restaurant: Optional[str] = None,
                       portion_multiplier: float = 1.0) -> int:
        """Insert a food log entry"""
        food_id = self._get_next_id(self.food_logs_file)
        timestamp = datetime.now().isoformat()
        
        row = {
            'id': food_id,
            'timestamp': timestamp,
            'food_name': food_name,
            'calories': calories,
            'protein': protein,
            'carbs': carbs,
            'fat': fat,
            'restaurant': restaurant or '',
            'portion_multiplier': portion_multiplier
        }
        
        fieldnames = ['id', 'timestamp', 'food_name', 'calories', 'protein', 
                     'carbs', 'fat', 'restaurant', 'portion_multiplier']
        self._append_csv(self.food_logs_file, row, fieldnames)
        return food_id
    
    def get_food_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get food logs, optionally filtered by date"""
        rows = self._read_csv(self.food_logs_file)
        
        if date:
            filtered = []
            for row in rows:
                row_date = row.get('timestamp', '')[:10]  # Get YYYY-MM-DD
                if row_date == date:
                    filtered.append(row)
            return filtered
        return rows
    
    # Water logs methods
    def insert_water_log(self, amount_ml: float, amount_oz: Optional[float] = None) -> int:
        """Insert a water log entry"""
        water_id = self._get_next_id(self.water_logs_file)
        timestamp = datetime.now().isoformat()
        
        if amount_oz is None:
            amount_oz = amount_ml / 29.5735
        
        row = {
            'id': water_id,
            'timestamp': timestamp,
            'amount_ml': amount_ml,
            'amount_oz': amount_oz
        }
        
        fieldnames = ['id', 'timestamp', 'amount_ml', 'amount_oz']
        self._append_csv(self.water_logs_file, row, fieldnames)
        return water_id
    
    def get_water_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get water logs, optionally filtered by date"""
        rows = self._read_csv(self.water_logs_file)
        
        if date:
            filtered = []
            for row in rows:
                row_date = row.get('timestamp', '')[:10]
                if row_date == date:
                    filtered.append(row)
            return filtered
        return rows
    
    # Gym logs methods
    def insert_gym_log(self, exercise: str, sets: Optional[int] = None,
                      reps: Optional[int] = None, weight: Optional[float] = None,
                      notes: Optional[str] = None) -> int:
        """Insert a gym log entry"""
        gym_id = self._get_next_id(self.gym_logs_file)
        timestamp = datetime.now().isoformat()
        
        row = {
            'id': gym_id,
            'timestamp': timestamp,
            'exercise': exercise,
            'sets': sets or '',
            'reps': reps or '',
            'weight': weight or '',
            'notes': notes or ''
        }
        
        fieldnames = ['id', 'timestamp', 'exercise', 'sets', 'reps', 'weight', 'notes']
        self._append_csv(self.gym_logs_file, row, fieldnames)
        return gym_id
    
    def get_gym_logs(self, date: Optional[str] = None) -> List[Dict]:
        """Get gym logs, optionally filtered by date"""
        rows = self._read_csv(self.gym_logs_file)
        
        if date:
            filtered = []
            for row in rows:
                row_date = row.get('timestamp', '')[:10]
                if row_date == date:
                    filtered.append(row)
            return filtered
        return rows
    
    # Reminders and todos methods
    def insert_reminder_todo(self, type: str, content: str, 
                            due_date: Optional[datetime] = None,
                            completed: bool = False) -> int:
        """Insert a reminder or todo entry"""
        item_id = self._get_next_id(self.reminders_todos_file)
        timestamp = datetime.now().isoformat()
        
        row = {
            'id': item_id,
            'timestamp': timestamp,
            'type': type,
            'content': content,
            'due_date': due_date.isoformat() if due_date else '',
            'completed': 'TRUE' if completed else 'FALSE',
            'completed_at': '',
            'sent_at': '',
            'follow_up_sent': 'FALSE',
            'decay_check_sent': 'FALSE'  # Track if decay check has been sent
        }
        
        fieldnames = ['id', 'timestamp', 'type', 'content', 'due_date', 'completed', 'completed_at', 'sent_at', 'follow_up_sent', 'decay_check_sent']
        self._append_csv(self.reminders_todos_file, row, fieldnames)
        return item_id
    
    def get_reminders_todos(self, type: Optional[str] = None, 
                           completed: Optional[bool] = None,
                           due_before: Optional[datetime] = None) -> List[Dict]:
        """Get reminders/todos with optional filters"""
        rows = self._read_csv(self.reminders_todos_file)
        
        filtered = []
        for row in rows:
            # Filter by type
            if type and row.get('type', '') != type:
                continue
            
            # Filter by completed status
            if completed is not None:
                row_completed = row.get('completed', 'FALSE').upper() == 'TRUE'
                if row_completed != completed:
                    continue
            
            # Filter by due date
            if due_before:
                due_date_str = row.get('due_date', '')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str)
                        if due_date > due_before:
                            continue
                    except:
                        pass
            
            filtered.append(row)
        
        return filtered
    
    def update_reminder_todo(self, item_id: int, completed: bool = True, sent_at: Optional[str] = None):
        """Update a reminder/todo to mark as completed or update sent status"""
        rows = self._read_csv(self.reminders_todos_file)
        
        # Define expected fieldnames
        fieldnames = ['id', 'timestamp', 'type', 'content', 'due_date', 'completed', 'completed_at', 'sent_at', 'follow_up_sent', 'decay_check_sent']
        
        # Ensure all rows have all required fields (for backward compatibility)
        for row in rows:
            # Ensure all fields exist with defaults
            for field in fieldnames:
                if field not in row:
                    if field == 'completed':
                        row[field] = 'FALSE'
                    elif field in ['completed_at', 'sent_at', 'due_date']:
                        row[field] = ''
                    elif field in ['follow_up_sent', 'decay_check_sent']:
                        row[field] = 'FALSE'
                    else:
                        row[field] = ''
        
        # Update the specific row
        for row in rows:
            if int(row.get('id', 0)) == item_id:
                if completed is not None:
                    row['completed'] = 'TRUE' if completed else 'FALSE'
                    if completed:
                        row['completed_at'] = datetime.now().isoformat()
                if sent_at is not None:
                    row['sent_at'] = sent_at
                break
        
        self._write_csv(self.reminders_todos_file, rows, fieldnames)
    
    def mark_follow_up_sent(self, item_id: int):
        """Mark that a follow-up has been sent for a reminder"""
        rows = self._read_csv(self.reminders_todos_file)
        
        # Define expected fieldnames (must match initialization)
        fieldnames = ['id', 'timestamp', 'type', 'content', 'due_date', 'completed', 'completed_at', 'sent_at', 'follow_up_sent', 'decay_check_sent']
        
        # Ensure all rows have all required fields (for backward compatibility)
        for row in rows:
            for field in fieldnames:
                if field not in row:
                    if field == 'completed':
                        row[field] = 'FALSE'
                    elif field in ['completed_at', 'sent_at', 'due_date']:
                        row[field] = ''
                    elif field in ['follow_up_sent', 'decay_check_sent']:
                        row[field] = 'FALSE'
                    else:
                        row[field] = ''
        
        # Update the specific row
        for row in rows:
            if int(row.get('id', 0)) == item_id:
                row['follow_up_sent'] = 'TRUE'
                break
        
        self._write_csv(self.reminders_todos_file, rows, fieldnames)
    
    def delete_old_logs(self, before_date: str):
        """Delete logs older than specified date (YYYY-MM-DD)"""
        # Food logs
        food_rows = self._read_csv(self.food_logs_file)
        food_filtered = [r for r in food_rows if r.get('timestamp', '')[:10] >= before_date]
        if len(food_filtered) < len(food_rows):
            fieldnames = ['id', 'timestamp', 'food_name', 'calories', 'protein', 
                         'carbs', 'fat', 'restaurant', 'portion_multiplier']
            self._write_csv(self.food_logs_file, food_filtered, fieldnames)
        
        # Water logs
        water_rows = self._read_csv(self.water_logs_file)
        water_filtered = [r for r in water_rows if r.get('timestamp', '')[:10] >= before_date]
        if len(water_filtered) < len(water_rows):
            fieldnames = ['id', 'timestamp', 'amount_ml', 'amount_oz']
            self._write_csv(self.water_logs_file, water_filtered, fieldnames)
        
        # Gym logs
        gym_rows = self._read_csv(self.gym_logs_file)
        gym_filtered = [r for r in gym_rows if r.get('timestamp', '')[:10] >= before_date]
        if len(gym_filtered) < len(gym_rows):
            fieldnames = ['id', 'timestamp', 'exercise', 'sets', 'reps', 'weight', 'notes']
            self._write_csv(self.gym_logs_file, gym_filtered, fieldnames)
        
        # Reminders/todos
        reminder_rows = self._read_csv(self.reminders_todos_file)
        reminder_filtered = [r for r in reminder_rows if r.get('timestamp', '')[:10] >= before_date]
        if len(reminder_filtered) < len(reminder_rows):
            # Define expected fieldnames
            fieldnames = ['id', 'timestamp', 'type', 'content', 'due_date', 'completed', 'completed_at', 'sent_at', 'follow_up_sent', 'decay_check_sent']
            
            # Ensure all rows have all required fields (for backward compatibility)
            for row in reminder_filtered:
                for field in fieldnames:
                    if field not in row:
                        if field == 'completed':
                            row[field] = 'FALSE'
                        elif field in ['completed_at', 'sent_at', 'due_date']:
                            row[field] = ''
                        elif field in ['follow_up_sent', 'decay_check_sent']:
                            row[field] = 'FALSE'
                        else:
                            row[field] = ''
            
            self._write_csv(self.reminders_todos_file, reminder_filtered, fieldnames)
    
    def get_stats(self) -> Dict[str, int]:
        """Get counts for all log types"""
        return {
            'food_logs': len(self._read_csv(self.food_logs_file)),
            'water_logs': len(self._read_csv(self.water_logs_file)),
            'gym_logs': len(self._read_csv(self.gym_logs_file)),
            'reminders_todos': len(self._read_csv(self.reminders_todos_file))
        }
    
    # Quote tracking methods
    def get_used_quotes(self) -> List[str]:
        """Get list of all quotes that have been used"""
        rows = self._read_csv(self.used_quotes_file)
        return [row.get('quote', '') for row in rows if row.get('quote', '')]
    
    def add_used_quote(self, quote: str, author: str = ''):
        """Record a quote as used"""
        today = datetime.now().date().isoformat()
        row = {
            'date': today,
            'quote': quote,
            'author': author
        }
        fieldnames = ['date', 'quote', 'author']
        self._append_csv(self.used_quotes_file, row, fieldnames)
    
    def get_todays_quote(self) -> Optional[Dict]:
        """Get today's quote if one was already fetched"""
        today = datetime.now().date().isoformat()
        rows = self._read_csv(self.used_quotes_file)
        for row in rows:
            if row.get('date') == today:
                return {
                    'quote': row.get('quote', ''),
                    'author': row.get('author', '')
                }
        return None
    
    # Water goals methods
    def get_water_goal(self, date: str, default_ml: float = 4000.0) -> float:
        """Get water goal for a specific date (YYYY-MM-DD), returns default if not set"""
        rows = self._read_csv(self.water_goals_file)
        for row in rows:
            if row.get('date') == date:
                goal_str = row.get('goal_ml', '')
                if goal_str:
                    try:
                        return float(goal_str)
                    except ValueError:
                        pass
        return default_ml
    
    def set_water_goal(self, date: str, goal_ml: float):
        """Set water goal for a specific date (YYYY-MM-DD)"""
        rows = self._read_csv(self.water_goals_file)
        
        # Check if goal already exists for this date
        updated = False
        for row in rows:
            if row.get('date') == date:
                row['goal_ml'] = goal_ml
                updated = True
                break
        
        # If not found, add new row
        if not updated:
            rows.append({
                'date': date,
                'goal_ml': goal_ml
            })
        
        fieldnames = ['date', 'goal_ml']
        self._write_csv(self.water_goals_file, rows, fieldnames)
    
    def get_todays_water_total(self, date: Optional[str] = None) -> float:
        """Get total water logged for a specific date (defaults to today)"""
        if date is None:
            date = datetime.now().date().isoformat()
        
        water_logs = self.get_water_logs(date)
        total_ml = 0.0
        for log in water_logs:
            amount_str = log.get('amount_ml', '0')
            if amount_str:
                try:
                    total_ml += float(amount_str)
                except ValueError:
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
                value_str = log.get(key, '0')
                if value_str:
                    try:
                        totals[key] += float(value_str)
                    except ValueError:
                        pass
        
        return totals

