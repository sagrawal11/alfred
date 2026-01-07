import os
import sys
import json
import atexit
import csv
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import random
import requests

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from gemini_nlp import create_gemini_processor
from communication_service import CommunicationService
from supabase_database import SupabaseDatabase
from google_calendar import create_calendar_service

# Check if another instance is already running
def check_single_instance():
    """Check if another instance of the app is already running"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 5001))
        sock.close()
        return True
    except OSError:
        print("Error: Another instance is already running on port 5001")
        print("Please stop the other instance first")
        return False

def daily_database_dump():
    """Archive old logs"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        db.delete_old_logs(today)
        print(f"Database cleanup completed: kept logs from {today} onwards")
    except Exception as e:
        print(f"Error during database cleanup: {e}")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize services
communication_service = CommunicationService()

# Load configuration
config = Config()

# Initialize Supabase database
if not config.SUPABASE_URL or not config.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
db = SupabaseDatabase(config.SUPABASE_URL, config.SUPABASE_KEY)

# Validate configuration
try:
    config.validate()
    print("Configuration validated successfully")
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set")
    exit(1)

# Ensure required directories exist
def ensure_directories():
    """Create required directories if they don't exist"""
    try:
        os.makedirs(config.DATABASE_DIR, exist_ok=True)
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating directories: {e}")
        import traceback
        traceback.print_exc()

# Create directories before initializing services
ensure_directories()

# Initialize Google services
# google_services = GoogleServicesManager() # This line is now redundant as it's initialized above

def check_reminders():
    """Check for due reminders and send notifications"""
    try:
        current_time = datetime.now()
        
        # Get all due reminders that haven't been sent yet
        due_reminders = db.get_reminders_todos(
            type='reminder',
            completed=False,
            due_before=current_time
        )
        
        for reminder in due_reminders:
            reminder_id = int(reminder.get('id', 0))
            content = reminder.get('content', '')
            sent_at = reminder.get('sent_at', '')
            
            # Only send if not already sent
            if not sent_at:
            # Send reminder via communication service
                user_phone = config.YOUR_PHONE_NUMBER
                message = f"REMINDER: {content}"
                
                if user_phone:
                    result = communication_service.send_response(message, user_phone)
                else:
                    result = communication_service.send_response(message)
                
                if result['success']:
                    print(f"Reminder sent via {result['method']}: {content}")
                    db.update_reminder_todo(reminder_id, completed=False, sent_at=current_time.isoformat())
                else:
                    print(f"Failed to send reminder: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"Error checking reminders: {e}")

def check_reminder_followups():
    """Check for reminders that were sent but not completed, and send follow-ups"""
    try:
        current_time = datetime.now()
        followup_delay = timedelta(minutes=config.REMINDER_FOLLOWUP_DELAY_MINUTES)
        
        # Get all reminders that were sent but not completed
        all_reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        for reminder in all_reminders:
            reminder_id = int(reminder.get('id', 0))
            content = reminder.get('content', '')
            sent_at_str = reminder.get('sent_at', '')
            follow_up_sent = reminder.get('follow_up_sent', 'FALSE').upper() == 'TRUE'
            
            # Skip if no sent_at timestamp or follow-up already sent
            if not sent_at_str or follow_up_sent:
                continue
            
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
                time_since_sent = current_time - sent_at
                
                # If enough time has passed, send follow-up
                if time_since_sent >= followup_delay:
                    user_phone = config.YOUR_PHONE_NUMBER
                    
                    # Check if we should suggest rescheduling (Feature 3)
                    due_date_str = reminder.get('due_date', '')
                    should_reschedule = False
                    reschedule_options = []
                    
                    if due_date_str and config.REMINDER_AUTO_RESCHEDULE_ENABLED:
                        try:
                            due_date = datetime.fromisoformat(due_date_str)
                            if due_date < current_time:
                                should_reschedule = True
                                # Generate reschedule options
                                tomorrow_morning = (current_time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                                later_today = current_time + timedelta(hours=2)
                                
                                if later_today.hour < 20:  # Only suggest if before 8pm
                                    reschedule_options.append({
                                        'time': later_today,
                                        'text': f"later today ({later_today.strftime('%I:%M %p')})"
                                    })
                                
                                reschedule_options.append({
                                    'time': tomorrow_morning,
                                    'text': f"tomorrow morning ({tomorrow_morning.strftime('%I:%M %p')})"
                                })
                        except:
                            pass
                    
                    # Build follow-up message
                    if should_reschedule and reschedule_options:
                        message = f"Did you get a chance to {content}, or should I reschedule it?\n"
                        message += "Reply:\n"
                        message += "• 'yes' or 'done' if completed\n"
                        for i, option in enumerate(reschedule_options[:3], 1):
                            message += f"• '{i}' to reschedule to {option['text']}\n"
                        message += "• 'no' to skip"
                        
                        # Store reschedule options for this reminder
                        if not hasattr(check_reminder_followups, 'pending_reschedules'):
                            check_reminder_followups.pending_reschedules = {}
                        check_reminder_followups.pending_reschedules[reminder_id] = reschedule_options
                    else:
                        message = f"Did you get a chance to {content}? Reply 'yes' if done, or 'no' to skip."
                    
                    if user_phone:
                        result = communication_service.send_response(message, user_phone)
                    else:
                        result = communication_service.send_response(message)
                    
                    if result['success']:
                        print(f"Follow-up sent for reminder: {content}")
                        db.mark_follow_up_sent(reminder_id)
                    else:
                        print(f"Failed to send follow-up: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error processing follow-up for reminder {reminder_id}: {e}")
                continue
        
    except Exception as e:
        print(f"Error checking reminder follow-ups: {e}")

def check_task_decay():
    """Check for stale todos and ask if they're still relevant"""
    try:
        if not config.TASK_DECAY_ENABLED:
            return
        
        current_time = datetime.now()
        decay_threshold = timedelta(days=config.TASK_DECAY_DAYS)
        
        # Get all incomplete todos
        all_todos = db.get_reminders_todos(type='todo', completed=False)
        
        for todo in all_todos:
            todo_id = int(todo.get('id', 0))
            content = todo.get('content', '')
            timestamp_str = todo.get('timestamp', '')
            decay_check_sent = todo.get('decay_check_sent', 'FALSE').upper() == 'TRUE'
            
            # Skip if decay check already sent
            if decay_check_sent:
                continue
            
            if not timestamp_str:
                continue
            
            try:
                created_at = datetime.fromisoformat(timestamp_str)
                age = current_time - created_at
                
                # If task is older than threshold, send decay check
                if age >= decay_threshold:
                    user_phone = config.YOUR_PHONE_NUMBER
                    message = f"Still want '{content}' on your list?\n"
                    message += "Reply:\n"
                    message += "• 'keep' to keep it\n"
                    message += "• 'reschedule' to move it\n"
                    message += "• 'delete' or 'remove' to remove it"
                    
                    if user_phone:
                        result = communication_service.send_response(message, user_phone)
                    else:
                        result = communication_service.send_response(message)
                    
                    if result['success']:
                        print(f"Task decay check sent for: {content}")
                        # Mark decay check as sent
                        db.mark_decay_check_sent(todo_id)
                        
                        # Store pending response
                        if not hasattr(check_task_decay, 'pending_responses'):
                            check_task_decay.pending_responses = {}
                        if user_phone not in check_task_decay.pending_responses:
                            check_task_decay.pending_responses[user_phone] = {}
                        check_task_decay.pending_responses[user_phone][todo_id] = content
                    else:
                        print(f"Failed to send task decay check: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f" Error processing task decay for todo {todo_id}: {e}")
                continue
        
    except Exception as e:
        print(f"Error checking task decay: {e}")

def send_weekly_digest():
    """Send weekly summary of behavior and progress"""
    try:
        if not config.WEEKLY_DIGEST_ENABLED:
            return
        
        today = datetime.now().date()
        
        # Calculate week boundaries (Monday to Sunday)
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        # Get all logs for the week
        all_water_logs = db.get_water_logs()
        all_food_logs = db.get_food_logs()
        all_gym_logs = db.get_gym_logs()
        all_todos = db.get_reminders_todos()
        
        # Filter to this week
        week_water = []
        week_food = []
        week_gym = []
        week_todos = []
        
        for log in all_water_logs:
            try:
                log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                if week_start <= log_date <= week_end:
                    week_water.append(log)
            except:
                pass
        
        for log in all_food_logs:
            try:
                log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                if week_start <= log_date <= week_end:
                    week_food.append(log)
            except:
                pass
        
        for log in all_gym_logs:
            try:
                log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                if week_start <= log_date <= week_end:
                    week_gym.append(log)
            except:
                pass
        
        for item in all_todos:
            try:
                item_date = datetime.fromisoformat(item.get('timestamp', '')).date()
                if week_start <= item_date <= week_end:
                    week_todos.append(item)
            except:
                pass
        
        # Calculate stats
        total_water_ml = sum(float(log.get('amount_ml', 0)) for log in week_water)
        avg_water_ml = total_water_ml / 7 if len(week_water) > 0 else 0
        
        total_calories = sum(float(log.get('calories', 0)) for log in week_food)
        avg_calories = total_calories / 7 if len(week_food) > 0 else 0
        
        gym_days = len(set(datetime.fromisoformat(log.get('timestamp', '')).date() for log in week_gym if log.get('timestamp')))
        
        completed_todos = sum(1 for item in week_todos if item.get('completed', 'FALSE').upper() == 'TRUE')
        total_todos = len(week_todos)
        completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
        
        # Build digest message
        message = f"Weekly Digest ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d')})\n\n"
        
        # Water
        if avg_water_ml > 0:
            liters = avg_water_ml / 1000
            message += f"Water: {liters:.1f}L/day avg\n"
        else:
            message += f"Water: No logs this week\n"
        
        # Food
        if avg_calories > 0:
            message += f"Food: {avg_calories:.0f} cal/day avg\n"
        else:
            message += f"Food: No logs this week\n"
        
        # Gym
        message += f"Gym: {gym_days} days\n"
        
        # Tasks
        if total_todos > 0:
            message += f"Tasks: {completed_todos}/{total_todos} completed ({completion_rate:.0f}%)\n"
        else:
            message += f"Tasks: No tasks this week\n"
        
        # Send digest
        user_phone = config.YOUR_PHONE_NUMBER
        if user_phone:
            result = communication_service.send_response(message, user_phone)
        else:
            result = communication_service.send_response(message)
        
        if result['success']:
            print(f"Weekly digest sent")
        else:
            print(f"Failed to send weekly digest: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"Error sending weekly digest: {e}")

def check_gentle_nudges():
    """Send gentle, context-aware nudges based on personal patterns"""
    try:
        if not config.GENTLE_NUDGES_ENABLED:
            return
        
        current_time = datetime.now()
        today = current_time.date().isoformat()
        current_hour = current_time.hour
        
        # Only send nudges during waking hours (8 AM - 10 PM)
        if current_hour < 8 or current_hour >= 22:
            return
        
        # Get today's stats
        water_total = db.get_todays_water_total(today)
        food_totals = db.get_todays_food_totals(today)
        
        # Calculate average water intake for past 7 days (excluding today)
        past_7_days_water = []
        for i in range(1, 8):
            date = (current_time.date() - timedelta(days=i)).isoformat()
            day_total = db.get_todays_water_total(date)
            if day_total > 0:
                past_7_days_water.append(day_total)
        
        avg_water = sum(past_7_days_water) / len(past_7_days_water) if past_7_days_water else 0
        
        # Calculate expected water at this hour (assuming even distribution)
        hours_elapsed = current_hour - 8  # Since 8 AM
        if hours_elapsed < 0:
            hours_elapsed = 0
        expected_water_at_hour = (avg_water / 14) * hours_elapsed if avg_water > 0 else 0  # 14 hours from 8 AM to 10 PM
        
        # Check if behind on water
        if avg_water > 0 and water_total < expected_water_at_hour * 0.8:  # 20% behind
            bottles_behind = int((expected_water_at_hour - water_total) / config.WATER_BOTTLE_SIZE_ML)
            if bottles_behind > 0:
                user_phone = config.YOUR_PHONE_NUMBER
                message = f"You're about {bottles_behind} bottle{'s' if bottles_behind > 1 else ''} behind your usual pace today"
                
                if user_phone:
                    result = communication_service.send_response(message, user_phone)
                else:
                    result = communication_service.send_response(message)
                
                if result['success']:
                    print(f"Gentle nudge sent: water reminder")
                return  # Only send one nudge per check
        
        # Check for no food logged yet (after 10 AM)
        if current_hour >= 10 and food_totals.get('calories', 0) == 0:
            user_phone = config.YOUR_PHONE_NUMBER
            message = "Haven't logged any food yet today - just a friendly reminder"
            
            if user_phone:
                result = communication_service.send_response(message, user_phone)
            else:
                result = communication_service.send_response(message)
            
            if result['success']:
                print(f"Gentle nudge sent: food reminder")
            return
        
        # Check for no gym in a while (if it's afternoon and no gym today)
        if current_hour >= 14:
            gym_logs = db.get_gym_logs(today)
            if not gym_logs:
                # Check last gym date
                all_gym = db.get_gym_logs()
                if all_gym:
                    all_gym.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                    last_gym_date_str = all_gym[0].get('timestamp', '')[:10]
                    try:
                        last_gym_date = datetime.fromisoformat(last_gym_date_str).date()
                        days_since = (current_time.date() - last_gym_date).days
                        
                        # Only nudge if it's been 2+ days
                        if days_since >= 2:
                            user_phone = config.YOUR_PHONE_NUMBER
                            message = f"It's been {days_since} days since your last workout - just a gentle reminder"
                            
                            if user_phone:
                                result = communication_service.send_response(message, user_phone)
                            else:
                                result = communication_service.send_response(message)
                            
                            if result['success']:
                                print(f"Gentle nudge sent: gym reminder")
                    except:
                        pass
        
    except Exception as e:
        print(f"Error checking gentle nudges: {e}")

# Initialize pending reschedules dict
check_reminder_followups.pending_reschedules = {}

# Initialize pending task decay responses dict
check_task_decay.pending_responses = {}

# Scheduler will be initialized after all functions are defined

@app.route('/csv/<filename>')
def view_csv(filename):
    """View the contents of a CSV file"""
    try:
        # Validate filename to prevent directory traversal
        allowed_files = ['food_logs.csv', 'water_logs.csv', 'gym_logs.csv', 'reminders_todos.csv']
        if filename not in allowed_files:
            return jsonify({'error': 'Invalid filename'}), 400
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        csv_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'CSV file not found'}), 404
        
        # Read CSV and return as JSON
        data = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)
        
        return jsonify({
            'filename': filename,
            'row_count': len(data),
            'data': data[:100],  # Limit to first 100 rows for performance
            'total_rows': len(data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error reading CSV: {str(e)}'}), 500

@app.route('/csvs')
def list_csvs():
    """List all available CSV files with their sizes"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        
        if not os.path.exists(data_dir):
            return jsonify({'csvs': []})
        
        csv_files = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(data_dir, filename)
                file_size = os.path.getsize(file_path)
                csv_files.append({
                    'filename': filename,
                    'size_bytes': file_size,
                    'size_kb': round(file_size / 1024, 2)
                })
        
        return jsonify({'csvs': csv_files})
        
    except Exception as e:
        return jsonify({'error': f'Error listing CSVs: {str(e)}'}), 500

# Add manual dump endpoint
@app.route('/dump', methods=['POST'])
def manual_dump():
    """Manual database dump endpoint"""
    try:
        daily_database_dump()
        return jsonify({
            'status': 'success',
            'message': 'Database dumped successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Dump failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# Database initialization
def init_db():
    """Initialize the CSV database (creates CSV files with headers if they don't exist)"""
    # CSV database initializes itself when created
    db._init_csv_files()
    print("CSV database initialized (all CSV files ready)")

# Load hardcoded food database
def load_food_database():
    try:
        with open(config.FOOD_DATABASE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty database if it doesn't exist
        return {}

FOOD_DATABASE = load_food_database()

# Core message processing
class EnhancedMessageProcessor:
    def __init__(self):
        # Load custom food database
        try:
            with open(config.FOOD_DATABASE_PATH, 'r') as f:
                custom_food_db = json.load(f)
                print("Custom food database loaded")
        except FileNotFoundError:
            print("Custom food database not found, using default")
            custom_food_db = FOOD_DATABASE
        
        self.nlp_processor = create_gemini_processor(custom_food_db)
        # Store pending confirmations: {phone_number: {intent, message, entities, reason}}
        self.pending_confirmations = {}
        # Store pending "what just happened" options: {phone_number: {options: [...], timestamp: ...}}
        self.pending_what_happened = {}
        # Store pending fact query matches: {phone_number: {matches: [...], query: ...}}
        self.pending_fact_query = {}
        # Store pending fact deletion matches: {phone_number: {matches: [...], key: ...}}
        self.pending_fact_deletion = {}
    
    def process_message(self, message_body, phone_number=None):
        """Main message processing pipeline using intelligent NLP"""
        # Check if this is a reschedule response
        if phone_number and hasattr(check_reminder_followups, 'pending_reschedules') and check_reminder_followups.pending_reschedules:
            reschedule_response = self.handle_reschedule_response(message_body, phone_number)
            if reschedule_response:
                return reschedule_response
        
        # Check if this is a numbered response to "what just happened" options
        if phone_number and phone_number in self.pending_what_happened:
            what_happened_response = self.handle_what_happened_selection(message_body, phone_number)
            if what_happened_response:
                return what_happened_response
        
        # Check if this is a numbered response to fact query matches
        if phone_number and phone_number in self.pending_fact_query:
            fact_query_response = self.handle_fact_query_selection(message_body, phone_number)
            if fact_query_response:
                return fact_query_response
        
        # Check if this is a numbered response to fact deletion matches
        if phone_number and phone_number in self.pending_fact_deletion:
            fact_deletion_response = self.handle_fact_deletion_selection(message_body, phone_number)
            if fact_deletion_response:
                return fact_deletion_response
        
        # Check if this is a confirmation response first
        if phone_number and phone_number in self.pending_confirmations:
            confirmation_response = self.handle_confirmation(message_body, phone_number)
            if confirmation_response:
                return confirmation_response
        
        # Use intelligent NLP processor to classify intent and extract entities
        intent = self.nlp_processor.classify_intent(message_body)
        entities = self.nlp_processor.extract_entities(message_body)
        
        print(f"Intelligent NLP Results:")
        print(f"Intent: {intent}")
        print(f"Entities: {entities}")
        
        # Process based on intent
        response = self.handle_intent(intent, message_body, entities, phone_number)
        if response:
            return response
        
        return self.fallback_response(message_body, phone_number)
    
    def handle_intent(self, intent, message, entities, phone_number=None):
        """Handle specific intent using intelligent NLP"""
        if intent == 'water_logging':
            return self.handle_water(message, entities)
        elif intent == 'food_logging':
            return self.handle_food(message, entities)
        elif intent == 'gym_workout':
            return self.handle_gym(message, entities)
        elif intent == 'todo_add':
            return self.handle_todo(message, entities)
        elif intent == 'reminder_set':
            return self.handle_reminder(message, entities)
        elif intent == 'water_goal_set':
            return self.handle_water_goal(message, entities)
        elif intent == 'stats_query':
            return self.handle_stats_query(message, entities)
        elif intent == 'task_complete':
            return self.handle_completion(message, entities)
        elif intent == 'vague_completion':
            return self.handle_vague_completion(message, entities, phone_number)
        elif intent == 'what_should_i_do':
            return self.handle_what_should_i_do(message, entities)
        elif intent == 'food_suggestion':
            return self.handle_food_suggestion(message, entities)
        elif intent == 'undo_edit':
            return self.handle_undo_edit(message, entities)
        elif intent == 'sleep_logging':
            return self.handle_sleep(message, entities)
        elif intent == 'fact_storage':
            return self.handle_fact_storage(message, entities, phone_number)
        elif intent == 'fact_query':
            return self.handle_fact_query(message, entities, phone_number)
        elif intent == 'confirmation':
            # Handle explicit confirmations (yes, yep, correct, etc.)
            return self.handle_confirmation(message, phone_number)
        elif intent == 'unknown':
            return self.fallback_response(message, phone_number)
        
        return None
    
    def handle_water(self, message, entities):
        """Handle water logging using enhanced NLP processor"""
        amount_ml = self.nlp_processor.parse_water_amount(message, entities)
        if amount_ml:
            self.log_water(amount_ml)
            
            # Get today's date
            today = datetime.now().date().isoformat()
            
            # Get today's total and goal
            today_total_ml = db.get_todays_water_total(today)
            today_goal_ml = db.get_water_goal(today, default_ml=config.DEFAULT_WATER_GOAL_ML)
            
            # Calculate remaining and bottles needed
            remaining_ml = max(0, today_goal_ml - today_total_ml)
            bottles_needed = max(0, int(round(remaining_ml / config.WATER_BOTTLE_SIZE_ML)))
            
            # Format response
            oz = round(amount_ml / 29.5735, 1)
            bottles_logged = round(amount_ml / config.WATER_BOTTLE_SIZE_ML, 1)
            
            # Determine if it's a full bottle or partial
            if bottles_logged >= 0.9:  # Close to 1 bottle
                bottle_text = "1 bottle" if bottles_logged < 1.5 else f"{int(bottles_logged)} bottles"
            else:
                bottle_text = f"{bottles_logged:.1f} bottles"
            
            response = f"Logged {bottle_text} of water ({amount_ml}ml)\n"
            response += f"Total for today: {int(today_total_ml)}mL"
            
            if remaining_ml > 0:
                response += f"\n Need about {bottles_needed} more {'bottle' if bottles_needed == 1 else 'bottles'} to hit your goal of {int(today_goal_ml)}mL today"
            else:
                response += f"\n You've hit your goal of {int(today_goal_ml)}mL today!"
            
            return response
        return None
    
    def log_water(self, amount_ml):
        """Log water intake to database"""
        db.insert_water_log(amount_ml)
    
    def handle_food(self, message, entities):
        """Handle food logging"""
        food_data = self.nlp_processor.parse_food(message)
        if food_data:
            # Extract nutrition info
            food_info = food_data['food_data']
            portion_mult = food_data['portion_multiplier']
            food_name = food_data.get('food_name', '')
            
            # Calculate actual nutrition based on portion
            calories = int(food_info.get('calories', 0) * portion_mult)
            protein = round(food_info.get('protein', 0) * portion_mult, 1)
            carbs = round(food_info.get('carbs', 0) * portion_mult, 1)
            fat = round(food_info.get('fat', 0) * portion_mult, 1)
            
            # Only log if we have at least a food name or some macros
            if food_name or calories > 0 or protein > 0 or carbs > 0 or fat > 0:
            # Log to database
                self.log_food(
                        food_name=food_name if food_name else "unknown food",
                    calories=calories,
                    protein=protein,
                    carbs=carbs,
                    fat=fat,
                        restaurant=food_data.get('restaurant'),
                    portion_multiplier=portion_mult
                )
                
                # Get today's date and totals
            today = datetime.now().date().isoformat()
            today_totals = db.get_todays_food_totals(today)
            
            # Format response
            serving_info = f"({food_info['serving_size']})" if 'serving_size' in food_info else ""
            food_display = food_name.replace('_', ' ').title() if food_name else "food"
            response = f"Logged {food_display}{serving_info}\n"
            response += f"This meal: {calories} cal, {protein}g protein, {carbs}g carbs, {fat}g fat\n"
            response += f"📈 Total today: {int(today_totals['calories'])} cal, {today_totals['protein']:.1f}g protein, {today_totals['carbs']:.1f}g carbs, {today_totals['fat']:.1f}g fat"
            return response
        
        return None
    
    def parse_food_from_entities(self, message, food_name):
        """Parse known food with portion multiplier"""
        # Find matching food in database
        for food_key, food_data in self.food_db.items():
            if food_data['display_name'].lower() == food_name.lower():
                # Handle portions using enhanced NLP processor
                multiplier = self.nlp_processor.parse_portion_multiplier(message)
                return {
                    'name': food_data['display_name'],
                    'calories': int(food_data['calories'] * multiplier),
                    'protein': round(food_data['protein'] * multiplier, 1),
                    'carbs': round(food_data['carbs'] * multiplier, 1),
                    'fat': round(food_data['fat'] * multiplier, 1)
                }
        return None
    
    def log_food(self, food_name, calories, protein, carbs, fat, restaurant=None, portion_multiplier=1.0):
        """Log food to database"""
        db.insert_food_log(food_name, calories, protein, carbs, fat, restaurant, portion_multiplier)
    
    def log_unknown_food(self, food_name):
        """Log unknown food"""
        db.insert_food_log(food_name, 0, 0, 0, 0, None, 1.0)
    
    def schedule_food_reminder(self, food_name):
        """Schedule evening reminder to add food to database"""
        reminder_time = datetime.now().replace(hour=config.EVENING_REMINDER_HOUR, minute=0, second=0, microsecond=0)
        if reminder_time <= datetime.now():
            reminder_time += timedelta(days=1)
        
        db.insert_reminder_todo(
            type='reminder',
            content=f"Add macros for '{food_name}' to food database",
            due_date=reminder_time
        )
    
    def handle_gym(self, message, entities):
        """Handle gym workout logging using enhanced NLP processor"""
        workout_data = self.nlp_processor.parse_gym_workout(message)
        if workout_data:
            self.log_gym_workout(workout_data)
            
            # Build response message
            exercises = workout_data['exercises']
            exercise_details = []
            for ex in exercises:
                name = ex.get('name', 'exercise')
                sets = ex.get('sets', [])
                
                if sets:
                    # Handle new format with multiple sets
                    set_details = []
                    for s in sets:
                        weight = s.get('weight')
                        reps = s.get('reps')
                        if weight and reps:
                            set_details.append(f"{weight}x{reps}")
                        elif weight:
                            set_details.append(f"{weight}")
                        elif reps:
                            set_details.append(f"x{reps}")
                    
                    if set_details:
                        detail = f"{name}: {', '.join(set_details)}"
                    else:
                        detail = name
                else:
                    # Fallback to old format
                    weight = ex.get('weight')
                    reps = ex.get('reps')
                    sets_count = ex.get('sets', 1)
                    
                    if weight and reps:
                        detail = f"{name} {weight}x{reps}"
                        if sets_count > 1:
                            detail += f"x{sets_count}"
                    elif weight:
                        detail = f"{name} {weight}"
                    else:
                        detail = name
                
                exercise_details.append(detail)
            
            response = f"Logged {workout_data.get('muscle_group', 'workout')} workout: {', '.join(exercise_details)}"
            return response
        
        return None
    
    def log_gym_workout(self, workout_data):
        """Log gym workout to database"""
        exercises = workout_data.get('exercises', [])
        if exercises:
            # Log each exercise
            for ex in exercises:
                exercise_name = f"{workout_data.get('muscle_group', 'workout')} - {ex.get('name', 'exercise')}"
                
                # Handle new format with multiple sets
                sets = ex.get('sets', [])
                if sets:
                    # Store all sets in notes, use first set for main fields
                    first_set = sets[0]
                    sets_count = len(sets)
                    reps = first_set.get('reps')
                    weight = first_set.get('weight')
                    
                    # Build detailed notes with all sets
                    set_details = []
                    for i, s in enumerate(sets, 1):
                        w = s.get('weight')
                        r = s.get('reps')
                        if w and r:
                            set_details.append(f"Set {i}: {w}x{r}")
                        elif w:
                            set_details.append(f"Set {i}: {w}")
                        elif r:
                            set_details.append(f"Set {i}: x{r}")
                    
                    notes = f"All sets: {', '.join(set_details)}"
                    if len(exercises) > 1:
                        notes = f"[{len(exercises)} exercises] " + notes
                    
                    db.insert_gym_log(
                        exercise=exercise_name,
                        sets=sets_count,
                        reps=reps,
                        weight=weight,
                        notes=notes
                    )
                else:
                    # Fallback to old format
                    db.insert_gym_log(
                        exercise=exercise_name,
                        sets=ex.get('sets', 1),
                        reps=ex.get('reps'),
                        weight=ex.get('weight'),
                        notes=json.dumps(ex) if len(exercises) > 1 else ''
                    )
    
    def handle_todo(self, message, entities):
        """Handle todo creation using enhanced NLP processor"""
        tasks = entities.get('tasks', [])
        if tasks:
            task = tasks[0]
            self.add_todo(task)
            return f"Added to todo list: {task}"
        return None
    
    def add_todo(self, task):
        """Add todo to database"""
        db.insert_reminder_todo(type='todo', content=task, due_date=None, completed=False)
    
    def handle_reminder(self, message, entities):
        """Handle reminder creation using enhanced NLP processor"""
        reminder_data = self.nlp_processor.parse_reminder(message)
        if reminder_data:
            # Store reminder in database
            self.schedule_reminder(reminder_data)
            
            # Format response
            time_str = reminder_data['due_date'].strftime("%I:%M %p")
            date_str = reminder_data['due_date'].strftime("%B %d")
            
            response = f"Reminder set: {reminder_data['content']} on {date_str} at {time_str}"
            if reminder_data.get('priority') == 'high':
                response += "(URGENT)"
            return response
        
        return None
    
    def schedule_reminder(self, reminder_data):
        """Schedule reminder to database"""
        db.insert_reminder_todo(
            type='reminder',
            content=reminder_data['content'],
            due_date=reminder_data.get('due_date'),
            completed=False
        )
    
    def handle_water_goal(self, message, entities):
        """Handle water goal setting"""
        goal_data = self.nlp_processor.parse_water_goal(message)
        if goal_data:
            goal_ml = goal_data['goal_ml']
            target_date = goal_data['date']
            
            # Set the goal in database
            db.set_water_goal(target_date, goal_ml)
            
            # Format date for display
            date_obj = datetime.fromisoformat(target_date).date()
            today = datetime.now().date()
            
            if date_obj == today:
                date_display = "today"
            elif date_obj == today + timedelta(days=1):
                date_display = "tomorrow"
            else:
                date_display = date_obj.strftime("%B %d")
            
            goal_liters = goal_ml / 1000
            response = f"Water goal set for {date_display}: {goal_liters}L ({int(goal_ml)}mL)"
            return response
        
        return None
    
    def handle_stats_query(self, message, entities):
        """Handle stats queries (how much eaten, drank, etc.)"""
        query_data = self.nlp_processor.parse_stats_query(message)
        today = datetime.now().date().isoformat()
        
        response_parts = []
        
        # Get water stats if requested
        if query_data.get('water') or query_data.get('all'):
            water_total_ml = db.get_todays_water_total(today)
            water_goal_ml = db.get_water_goal(today, default_ml=config.DEFAULT_WATER_GOAL_ML)
            water_liters = water_total_ml / 1000
            goal_liters = water_goal_ml / 1000
            
            if water_total_ml > 0:
                bottles = round(water_total_ml / config.WATER_BOTTLE_SIZE_ML, 1)
                response_parts.append(f"Water: {water_liters:.1f}L ({int(water_total_ml)}mL, ~{bottles} bottles)")
                if water_total_ml >= water_goal_ml:
                    response_parts.append(f"    Goal reached! ({goal_liters:.1f}L)")
                else:
                    remaining = water_goal_ml - water_total_ml
                    remaining_liters = remaining / 1000
                    bottles_needed = int(round(remaining / config.WATER_BOTTLE_SIZE_ML))
                    response_parts.append(f"    {remaining_liters:.1f}L remaining ({bottles_needed} bottles) to reach {goal_liters:.1f}L goal")
            else:
                response_parts.append(f"Water: 0L (goal: {goal_liters:.1f}L)")
        
        # Get food stats if requested
        if query_data.get('food') or query_data.get('all'):
            food_totals = db.get_todays_food_totals(today)
            if food_totals['calories'] > 0:
                response_parts.append(f"Food: {int(food_totals['calories'])} cal")
                response_parts.append(f"{food_totals['protein']:.1f}g protein, {food_totals['carbs']:.1f}g carbs, {food_totals['fat']:.1f}g fat")
            else:
                response_parts.append(f"Food: No meals logged today")
        
        # Get gym stats if requested
        if query_data.get('gym') or query_data.get('all'):
            gym_logs = db.get_gym_logs(today)
            if gym_logs:
                response_parts.append(f"Gym: {len(gym_logs)} workout{'s' if len(gym_logs) != 1 else ''} logged today")
            else:
                response_parts.append(f"Gym: No workouts logged today")
        
        # Get sleep stats if requested
        if query_data.get('sleep') or query_data.get('all'):
            sleep_logs = db.get_sleep_logs(today)
            if sleep_logs:
                latest = sleep_logs[-1]  # Most recent
                duration = float(latest.get('duration_hours', 0))
                sleep_time = latest.get('sleep_time', '')
                wake_time = latest.get('wake_time', '')
                response_parts.append(f"Sleep: {duration:.1f} hours ({sleep_time} to {wake_time})")
            else:
                # Check yesterday
                yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
                yesterday_sleep = db.get_sleep_logs(yesterday)
                if yesterday_sleep:
                    latest = yesterday_sleep[-1]
                    duration = float(latest.get('duration_hours', 0))
                    sleep_time = latest.get('sleep_time', '')
                    wake_time = latest.get('wake_time', '')
                    response_parts.append(f"Sleep (yesterday): {duration:.1f} hours ({sleep_time} to {wake_time})")
                else:
                    response_parts.append(f"Sleep: No sleep logged")
        
        # Get todos if requested
        if query_data.get('todos') or query_data.get('all'):
            todos = db.get_reminders_todos(type='todo', completed=False)
            # Filter for today's todos (or all incomplete if no date filter)
            today_date = datetime.now().date()
            today_todos = []
            for todo in todos:
                # Todos without due dates are always shown
                due_date_str = todo.get('due_date', '')
                if not due_date_str:
                    today_todos.append(todo)
                else:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                        if due_date <= today_date:
                            today_todos.append(todo)
                    except:
                        today_todos.append(todo)
            
            if today_todos:
                todo_list = []
                for i, todo in enumerate(today_todos[:10], 1):  # Limit to 10
                    content = todo.get('content', '')
                    due_date_str = todo.get('due_date', '')
                    if due_date_str:
                        try:
                            due_date = datetime.fromisoformat(due_date_str).date()
                            if due_date == today_date:
                                todo_list.append(f"  {i}. {content} (today)")
                            else:
                                todo_list.append(f"  {i}. {content}")
                        except:
                            todo_list.append(f"  {i}. {content}")
                    else:
                        todo_list.append(f"  {i}. {content}")
                
                response_parts.append(f"Todos ({len(today_todos)}):")
                response_parts.extend(todo_list)
                if len(today_todos) > 10:
                    response_parts.append(f"   ... and {len(today_todos) - 10} more")
            else:
                response_parts.append(f"Todos: No todos for today")
        
        # Get reminders if requested
        if query_data.get('reminders') or query_data.get('all'):
            all_reminders = db.get_reminders_todos(type='reminder', completed=False)
            today_date = datetime.now().date()
            today_reminders = []
            
            for reminder in all_reminders:
                due_date_str = reminder.get('due_date', '')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                        # Show reminders for today or past (overdue)
                        if due_date <= today_date:
                            today_reminders.append(reminder)
                    except:
                        pass
            
            if today_reminders:
                # Sort by due date
                today_reminders.sort(key=lambda x: x.get('due_date', ''))
                
                reminder_list = []
                for i, reminder in enumerate(today_reminders[:10], 1):  # Limit to 10
                    content = reminder.get('content', '')
                    due_date_str = reminder.get('due_date', '')
                    if due_date_str:
                        try:
                            due_date = datetime.fromisoformat(due_date_str)
                            time_str = due_date.strftime("%I:%M %p")
                            date_str = due_date.strftime("%B %d")
                            
                            if due_date.date() == today_date:
                                reminder_list.append(f"  {i}. {content} at {time_str}")
                            else:
                                reminder_list.append(f"  {i}. {content} on {date_str} at {time_str}")
                        except:
                            reminder_list.append(f"  {i}. {content}")
                    else:
                        reminder_list.append(f"  {i}. {content}")
                
                response_parts.append(f"Reminders ({len(today_reminders)}):")
                response_parts.extend(reminder_list)
                if len(today_reminders) > 10:
                    response_parts.append(f"  ... and {len(today_reminders) - 10} more")
            else:
                response_parts.append(f"Reminders: No reminders for today")
        
        # Get calendar events if requested (and calendar service is available)
        # Try to get calendar_service, handle case where it doesn't exist
        calendar_service = None
        try:
            import sys
            if hasattr(sys.modules.get('__main__', None), 'calendar_service'):
                calendar_service = sys.modules['__main__'].calendar_service
        except:
            pass
        
        if calendar_service and (query_data.get('reminders') or query_data.get('todos') or query_data.get('all')):
            try:
                calendar_events = calendar_service.get_todays_events()
                if calendar_events:
                    event_list = []
                    for i, event in enumerate(calendar_events[:10], 1):  # Limit to 10
                        formatted = calendar_service.format_event_for_display(event)
                        event_list.append(f"  {i}. {formatted}")
                    
                    response_parts.append(f"Calendar Events ({len(calendar_events)}):")
                    response_parts.extend(event_list)
                    if len(calendar_events) > 10:
                        response_parts.append(f"  ... and {len(calendar_events) - 10} more")
                else:
                    response_parts.append(f"Calendar: No events scheduled for today")
            except Exception as e:
                print(f" Error fetching calendar events: {e}")
                # Don't add calendar section if there's an error
        
        if response_parts:
            # Determine header based on what's being shown
            if query_data.get('todos') and not query_data.get('all') and not query_data.get('food') and not query_data.get('water') and not query_data.get('gym'):
                return "Your Todos:\n" + "\n".join(response_parts)
            elif query_data.get('reminders') and not query_data.get('all') and not query_data.get('food') and not query_data.get('water') and not query_data.get('gym') and not query_data.get('todos'):
                return "Your Reminders:\n" + "\n".join(response_parts)
            else:
                return "Today's Stats:\n" + "\n".join(response_parts)
        
        return "No stats available for today"
    
    def handle_completion(self, message, entities):
        """Handle task/reminder completions"""
        # Try to match and complete tasks/reminders based on message content
        completed_item = self.mark_task_complete(message)
        if completed_item:
            item_type = completed_item.get('type', 'task')
            content = completed_item.get('content', 'item')
            if item_type == 'reminder':
                return f"Reminder completed: {content}"
            else:
                return f"Todo completed: {content}"
        return "I couldn't find a matching task or reminder to mark as complete."
    
    def mark_task_complete(self, message):
        """Mark task/reminder as complete by matching message content"""
        message_lower = message.lower()
        
        # Get all incomplete todos and reminders
        todos = db.get_reminders_todos(type='todo', completed=False)
        reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        all_items = []
        for todo in todos:
            all_items.append({**todo, 'item_type': 'todo', 'id': todo.get('id')})
        for reminder in reminders:
            all_items.append({**reminder, 'item_type': 'reminder', 'id': reminder.get('id')})
        
        # Try to find best match by content similarity
        best_match = None
        best_score = 0
        
        for item in all_items:
            content = item.get('content', '').lower()
            if not content:
                continue
            
            # Calculate match score
            score = 0
            
            # Check if key words from message appear in content
            message_words = set(message_lower.split())
            content_words = set(content.split())
            
            # Count matching words
            matching_words = message_words.intersection(content_words)
            # Remove common words that don't help matching
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'to', 'for', 'of', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'can', 'must'}
            matching_words = matching_words - common_words
            
            if matching_words:
                score = len(matching_words) / max(len(message_words - common_words), 1)
            
            # Bonus for exact phrase match
            if message_lower in content or content in message_lower:
                score += 0.5
            
            # Bonus if message contains action words that match common completion patterns
            completion_actions = ['called', 'went', 'did', 'finished', 'completed', 'done', 'bought', 'got', 'sent', 'emailed', 'texted']
            if any(action in message_lower for action in completion_actions):
                # Check if the action makes sense with the content
                for action in completion_actions:
                    if action in message_lower:
                        # If content mentions something related to the action, boost score
                        if any(word in content for word in message_lower.split() if word != action):
                            score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = item
        
        # If we found a reasonable match (score > 0.2), mark it as complete
        if best_match and best_score > 0.2:
            item_id = int(best_match.get('id', 0))
            db.update_reminder_todo(item_id, completed=True)
            
            # Clear any pending reschedule for this reminder
            if hasattr(check_reminder_followups, 'pending_reschedules'):
                if item_id in check_reminder_followups.pending_reschedules:
                    del check_reminder_followups.pending_reschedules[item_id]
            
            return {
                'type': best_match.get('item_type', 'todo'),
                'content': best_match.get('content', ''),
                'id': item_id
            }
        
        # Fallback: if no good match, try to complete most recent todo
        if todos:
            todos.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            most_recent = todos[0]
            item_id = int(most_recent.get('id', 0))
            db.update_reminder_todo(item_id, completed=True)
            return {
                'type': 'todo',
                'content': most_recent.get('content', '')
            }
        
        return None
    
    def handle_vague_completion(self, message, entities, phone_number=None):
        """Handle vague completion messages with 'What just happened?' mode"""
        # Generate likely interpretations
        options = self._generate_completion_options(message)
        
        if not options:
            # Fallback to regular completion handling
            return self.handle_completion(message, entities)
        
        # Store options for confirmation
        if phone_number:
            self.pending_what_happened[phone_number] = {
                'options': options,
                'timestamp': datetime.now().isoformat(),
                'original_message': message
            }
        
        # Format response with numbered options
        response = "🤔 What just happened? Pick a number:\n"
        for i, option in enumerate(options, 1):
            response += f"{i}. {option['description']}\n"
        
            return response
        
    def _generate_completion_options(self, message):
        """Generate likely interpretations for vague completion messages"""
        message_lower = message.lower()
        options = []
        
        # Get recent activity context
        today = datetime.now().date().isoformat()
        recent_gym = db.get_gym_logs(today)
        recent_food = db.get_food_logs(today)
        recent_water = db.get_water_logs(today)
        todos = db.get_reminders_todos(type='todo', completed=False)
        reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        # Check for workout context (recent gym activity)
        if recent_gym:
            options.append({
                'type': 'gym',
                'description': 'Workout/Gym session',
                'action': 'gym_workout'
            })
        
        # Check for task/reminder completion
        if todos or reminders:
            # Get most recent items
            all_items = []
            for todo in todos[:3]:
                all_items.append({'type': 'todo', 'content': todo.get('content', ''), 'id': todo.get('id')})
            for reminder in reminders[:3]:
                all_items.append({'type': 'reminder', 'content': reminder.get('content', ''), 'id': reminder.get('id')})
            
            if all_items:
                # Add top 2 most likely tasks
                for item in all_items[:2]:
                    item_type = item['type']
                    content = item['content'][:30]  # Truncate long content
                    options.append({
                        'type': item_type,
                        'description': f"Task: {content}",
                        'action': 'task_complete',
                        'item_id': item.get('id'),
                        'item_content': item['content']
                    })
        
        # Check for meal context (recent food activity)
        if recent_food:
            # Check if it's been a while since last meal (might be logging a meal)
            if len(recent_food) > 0:
                options.append({
                    'type': 'food',
                    'description': 'Meal/Food',
                    'action': 'food_logging'
                })
        
        # Always include generic options
        if not any(opt['type'] == 'water' for opt in options):
            options.append({
                'type': 'water',
                'description': 'Water/Drink',
                'action': 'water_logging'
            })
        
        # Limit to 5 options max
        return options[:5]
    
    def handle_what_happened_selection(self, message, phone_number):
        """Handle user's selection from 'what just happened' options"""
        if phone_number not in self.pending_what_happened:
            return None
    
        pending = self.pending_what_happened[phone_number]
        options = pending['options']
        
        # Parse selection (could be "1", "one", "first", etc.)
        message_lower = message.lower().strip()
        
        # Try to extract number
        import re
        numbers = re.findall(r'\d+', message_lower)
        if numbers:
            selection = int(numbers[0])
            if 1 <= selection <= len(options):
                selected_option = options[selection - 1]
                
                # Remove from pending
                del self.pending_what_happened[phone_number]
                
                # Execute the selected action
                return self._execute_completion_action(selected_option, pending['original_message'])
        
        # If not a number, try to match by description
        for i, option in enumerate(options, 1):
            if any(word in message_lower for word in option['description'].lower().split()):
                selected_option = option
                del self.pending_what_happened[phone_number]
                return self._execute_completion_action(selected_option, pending['original_message'])
        
        return f"Please reply with a number (1-{len(options)})"
    
    def _execute_completion_action(self, option, original_message):
        """Execute the action based on selected option"""
        action_type = option.get('action')
        
        if action_type == 'task_complete':
            # Mark the specific task as complete
            item_content = option.get('item_content', '')
            if item_content:
                # Find and complete the matching task
                todos = db.get_reminders_todos(type='todo', completed=False)
                reminders = db.get_reminders_todos(type='reminder', completed=False)
                
                all_items = todos + reminders
                for item in all_items:
                    if item.get('content', '').lower() == item_content.lower():
                        item_id = int(item.get('id', 0))
                        db.update_reminder_todo(item_id, completed=True)
                        item_type = item.get('type', 'task')
                        return f"{item_type.title()} completed: {item_content}"
            
            # Fallback to regular completion
            return self.handle_completion(original_message, {})
        
        elif action_type == 'gym_workout':
            # Try to parse as gym workout
            return self.handle_gym(original_message, {}) or "Logged as workout"
        
        elif action_type == 'food_logging':
            # Try to parse as food
            return self.handle_food(original_message, {}) or "Logged as meal"
        
        elif action_type == 'water_logging':
            # Try to parse as water
            return self.handle_water(original_message, {}) or "Logged as water"
        
        return "Got it!"
    
    def handle_what_should_i_do(self, message, entities):
        """Handle 'What should I do now?' queries - synthesize context and suggest actions"""
        current_time = datetime.now()
        today = current_time.date().isoformat()
        current_hour = current_time.hour
        
        suggestions = []
        
        # Check water intake
        water_total = db.get_todays_water_total(today)
        water_goal = db.get_water_goal(today, default_ml=config.DEFAULT_WATER_GOAL_ML)
        if water_total < water_goal * 0.7:  # Less than 70% of goal
            remaining = water_goal - water_total
            bottles_needed = int(round(remaining / config.WATER_BOTTLE_SIZE_ML))
            if bottles_needed > 0:
                suggestions.append(f"Drink water ({bottles_needed} bottle{'s' if bottles_needed > 1 else ''} to reach goal)")
        
        # Check for incomplete todos/reminders
        todos = db.get_reminders_todos(type='todo', completed=False)
        reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        # Filter for today's items
        today_date = current_time.date()
        today_todos = []
        for todo in todos:
            due_date_str = todo.get('due_date', '')
            if not due_date_str:
                today_todos.append(todo)
            else:
                try:
                    due_date = datetime.fromisoformat(due_date_str).date()
                    if due_date <= today_date:
                        today_todos.append(todo)
                except:
                    today_todos.append(todo)
        
        today_reminders = []
        for reminder in reminders:
            due_date_str = reminder.get('due_date', '')
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str).date()
                    if due_date <= today_date:
                        today_reminders.append(reminder)
                except:
                    pass
        
        # Add top 2-3 most urgent todos
        if today_todos:
            for todo in today_todos[:2]:
                content = todo.get('content', '')[:40]
                suggestions.append(f"{content}")
        
        # Add upcoming reminders (if within next 2 hours)
        if today_reminders:
            for reminder in today_reminders[:2]:
                due_date_str = reminder.get('due_date', '')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str)
                        hours_until = (due_date - current_time).total_seconds() / 3600
                        if 0 <= hours_until <= 2:
                            content = reminder.get('content', '')[:40]
                            time_str = due_date.strftime("%I:%M %p")
                            suggestions.append(f"{content} (at {time_str})")
                    except:
                        pass
        
        # Check food intake (if it's meal time and no food logged)
        food_totals = db.get_todays_food_totals(today)
        if food_totals['calories'] == 0:
            if 12 <= current_hour <= 14:  # Lunch time
                suggestions.append("Log lunch")
            elif 18 <= current_hour <= 20:  # Dinner time
                suggestions.append("Log dinner")
        
        # Check gym (if afternoon and no workout today)
        if current_hour >= 17:
            gym_logs = db.get_gym_logs(today)
            if not gym_logs:
                suggestions.append("Consider a workout")
        
        # Format response
        if suggestions:
            response = "Here's what you could do:\n\n"
            for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5
                response += f"{i}. {suggestion}\n"
            return response
        else:
            return "You're all caught up! Nothing urgent right now. Great job!"
    
    def handle_undo_edit(self, message, entities):
        """Handle undo/delete commands for last entries"""
        message_lower = message.lower()
        
        # Determine what type to undo based on entities or message content
        food_items = entities.get('food_items', [])
        
        # Check message for type indicators
        if 'water' in message_lower or any('water' in item.lower() for item in food_items):
            # Undo last water entry
            water_logs = db.get_water_logs()
            if water_logs:
                water_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_water = water_logs[0]
                water_id = int(last_water.get('id', 0))
                amount_ml = last_water.get('amount_ml', '0')
                
                # Delete by rewriting CSV without this entry
                db.delete_water_log(water_id)
                
                return f"Removed last water entry ({amount_ml}ml)"
            return "No water entries to remove"
        
        elif 'food' in message_lower or 'meal' in message_lower or any(item.lower() != 'water' for item in food_items):
            # Undo last food entry
            food_logs = db.get_food_logs()
            if food_logs:
                food_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_food = food_logs[0]
                food_id = int(last_food.get('id', 0))
                food_name = last_food.get('food_name', 'item')
                
                # Delete by rewriting CSV without this entry
                db.delete_food_log(food_id)
                
                return f"Removed last food entry: {food_name}"
            return "No food entries to remove"
        
        elif 'gym' in message_lower or 'workout' in message_lower or 'exercise' in message_lower:
            # Undo last gym entry
            gym_logs = db.get_gym_logs()
            if gym_logs:
                gym_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_gym = gym_logs[0]
                gym_id = int(last_gym.get('id', 0))
                exercise = last_gym.get('exercise', 'workout')
                
                # Delete by rewriting CSV without this entry
                db.delete_gym_log(gym_id)
                
                return f"Removed last gym entry: {exercise}"
            return "No gym entries to remove"
        
        elif 'todo' in message_lower or 'task' in message_lower:
            # Undo last todo
            todos = db.get_reminders_todos(type='todo', completed=False)
            if todos:
                todos.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_todo = todos[0]
                todo_id = int(last_todo.get('id', 0))
                content = last_todo.get('content', 'item')
                
                # Delete by rewriting CSV without this entry
                db.delete_reminder_todo(todo_id)
                
                return f"Removed last todo: {content}"
            return "No todos to remove"
        
        elif 'reminder' in message_lower:
            # Undo last reminder
            reminders = db.get_reminders_todos(type='reminder', completed=False)
            if reminders:
                reminders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_reminder = reminders[0]
                reminder_id = int(last_reminder.get('id', 0))
                content = last_reminder.get('content', 'item')
                
                # Delete by rewriting CSV without this entry
                db.delete_reminder_todo(reminder_id)
                
                return f"Removed last reminder: {content}"
            return "No reminders to remove"
        
        # Default: try to undo most recent entry of any type
        # Check water first (most common)
        water_logs = db.get_water_logs()
        food_logs = db.get_food_logs()
        gym_logs = db.get_gym_logs()
        todos = db.get_reminders_todos(type='todo', completed=False)
        
        # Find most recent entry
        all_entries = []
        if water_logs:
            last_water = max(water_logs, key=lambda x: x.get('timestamp', ''))
            all_entries.append(('water', last_water.get('timestamp', ''), last_water))
        if food_logs:
            last_food = max(food_logs, key=lambda x: x.get('timestamp', ''))
            all_entries.append(('food', last_food.get('timestamp', ''), last_food))
        if gym_logs:
            last_gym = max(gym_logs, key=lambda x: x.get('timestamp', ''))
            all_entries.append(('gym', last_gym.get('timestamp', ''), last_gym))
        if todos:
            last_todo = max(todos, key=lambda x: x.get('timestamp', ''))
            all_entries.append(('todo', last_todo.get('timestamp', ''), last_todo))
        
        if all_entries:
            # Sort by timestamp and get most recent
            all_entries.sort(key=lambda x: x[1], reverse=True)
            entry_type, _, entry = all_entries[0]
            
            # Recursively call with the determined type
            if entry_type == 'water':
                return self.handle_undo_edit("undo last water", entities)
            elif entry_type == 'food':
                return self.handle_undo_edit("undo last food", entities)
            elif entry_type == 'gym':
                return self.handle_undo_edit("undo last gym", entities)
            elif entry_type == 'todo':
                return self.handle_undo_edit("undo last todo", entities)
        
        return "No recent entries found to remove"
    
    def handle_food_suggestion(self, message, entities):
        """Handle food suggestion requests"""
        constraints = self.nlp_processor.parse_food_suggestion(message)
        
        # Get all foods from database
        food_db = self.nlp_processor.food_db
        if not food_db:
            return "No food database available for suggestions."
        
        # Get today's food totals for context
        today = datetime.now().date().isoformat()
        today_totals = db.get_todays_food_totals(today)
        
        # Get past food logs (to prioritize foods you've eaten before)
        past_foods = {}
        food_logs = db.get_food_logs()
        for log in food_logs[-50:]:  # Last 50 logs
            food_name = log.get('food_name', '').lower().strip()
            restaurant = log.get('restaurant', '').lower().strip()
            if food_name:
                key = f"{restaurant} {food_name}" if restaurant else food_name
                past_foods[key] = past_foods.get(key, 0) + 1
        
        # Score and filter foods
        scored_foods = []
        for food_key, food_data in food_db.items():
            # Skip entries without proper structure
            if not isinstance(food_data, dict):
                continue
            
            # Get macros (handle different field names)
            calories = float(food_data.get('calories', 0) or food_data.get('cal', 0) or 0)
            protein = float(food_data.get('protein_g', 0) or food_data.get('protein', 0) or 0)
            carbs = float(food_data.get('carbs_g', 0) or food_data.get('carbs', 0) or 0)
            fat = float(food_data.get('fat_g', 0) or food_data.get('fat', 0) or 0)
            
            # Skip foods with no macros
            if calories == 0 and protein == 0 and carbs == 0 and fat == 0:
                continue
            
            restaurant = food_data.get('restaurant', '')
            food_name = food_key.replace('_', ' ').title()
            
            # Filter by restaurant if specified
            if constraints.get('restaurant'):
                if restaurant.lower() != constraints['restaurant'].lower():
                    continue
            
            # Calculate match score based on constraints
            score = 0.0
            matches_constraints = True
            
            # High/low protein
            if constraints.get('high_protein'):
                if protein < 20:  # Threshold for "high protein"
                    matches_constraints = False
                else:
                    score += protein / 10  # Higher protein = higher score
            elif constraints.get('low_protein'):
                if protein > 15:
                    matches_constraints = False
                else:
                    score += (20 - protein) / 10
            
            # High/low calories
            if constraints.get('high_calories'):
                if calories < 400:
                    matches_constraints = False
                else:
                    score += calories / 100
            elif constraints.get('low_calories'):
                if calories > 400:
                    matches_constraints = False
                else:
                    score += (500 - calories) / 100
            
            # High/low carbs
            if constraints.get('high_carbs'):
                if carbs < 40:
                    matches_constraints = False
                else:
                    score += carbs / 10
            elif constraints.get('low_carbs'):
                if carbs > 30:
                    matches_constraints = False
                else:
                    score += (40 - carbs) / 10
            
            # High/low fat
            if constraints.get('high_fat'):
                if fat < 20:
                    matches_constraints = False
                else:
                    score += fat / 10
            elif constraints.get('low_fat'):
                if fat > 15:
                    matches_constraints = False
                else:
                    score += (20 - fat) / 10
            
            # If constraints specified but don't match, skip
            has_constraints = any([
                constraints.get('high_protein'), constraints.get('low_protein'),
                constraints.get('high_calories'), constraints.get('low_calories'),
                constraints.get('high_carbs'), constraints.get('low_carbs'),
                constraints.get('high_fat'), constraints.get('low_fat')
            ])
            if has_constraints and not matches_constraints:
                continue
            
            # Bonus: foods you've eaten before
            if food_key.lower() in past_foods:
                score += past_foods[food_key.lower()] * 0.5
            
            # Consider remaining macros (if we have daily goals)
            # For now, just use score
            
            scored_foods.append({
                'name': food_name,
                'restaurant': restaurant,
                'calories': calories,
                'protein': protein,
                'carbs': carbs,
                'fat': fat,
                'score': score
            })
        
        # Sort by score (descending) and take top 5
        scored_foods.sort(key=lambda x: x['score'], reverse=True)
        suggestions = scored_foods[:5]
        
        if not suggestions:
            return "No foods match your criteria. Try different constraints or check your food database."
        
        # Format response (concise: names, macros, nothing else)
        response_parts = []
        for i, food in enumerate(suggestions, 1):
            name = food['name']
            if food['restaurant']:
                name = f"{food['restaurant'].title()} {name}"
            
            response_parts.append(
                f"{i}. {name}: {int(food['calories'])} cal, {food['protein']:.0f}g protein, "
                f"{food['carbs']:.0f}g carbs, {food['fat']:.0f}g fat"
            )
        
        return '\n'.join(response_parts)
    
    def handle_sleep(self, message, entities):
        """Handle sleep logging"""
        import re
        from datetime import datetime, timedelta
        
        message_lower = message.lower()
        
        # Try to parse sleep times from message
        # Patterns: "slept at 1:30", "up at 8", "slept 1:30-8", "went to bed at 11", "woke up at 7"
        sleep_time = None
        wake_time = None
        
        # Look for time patterns
        time_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        all_times = re.findall(time_pattern, message_lower)
        
        # Look for sleep/wake keywords
        if 'slept' in message_lower or 'bed' in message_lower or 'sleep' in message_lower:
            # Find sleep time
            for match in all_times:
                hour = int(match[0])
                minute = int(match[1]) if match[1] else 0
                am_pm = match[2].lower() if match[2] else ''
                
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                
                # Sleep time is usually later in the day (after 6pm) or earlier (before 6am)
                if hour >= 18 or hour < 6:
                    sleep_time = f"{hour:02d}:{minute:02d}"
                    break
        
        if 'up' in message_lower or 'woke' in message_lower or 'wake' in message_lower:
            # Find wake time
            for match in all_times:
                hour = int(match[0])
                minute = int(match[1]) if match[1] else 0
                am_pm = match[2].lower() if match[2] else ''
                
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                
                # Wake time is usually morning (6am-12pm)
                if 6 <= hour < 12:
                    wake_time = f"{hour:02d}:{minute:02d}"
                    break
        
        # Try range format: "slept 1:30-8"
        range_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        range_match = re.search(range_pattern, message_lower)
        if range_match:
            # First time is sleep, second is wake
            sleep_hour = int(range_match.group(1))
            sleep_min = int(range_match.group(2)) if range_match.group(2) else 0
            sleep_ampm = range_match.group(3).lower() if range_match.group(3) else ''
            
            wake_hour = int(range_match.group(4))
            wake_min = int(range_match.group(5)) if range_match.group(5) else 0
            wake_ampm = range_match.group(6).lower() if range_match.group(6) else ''
            
            if sleep_ampm == 'pm' and sleep_hour != 12:
                sleep_hour += 12
            elif sleep_ampm == 'am' and sleep_hour == 12:
                sleep_hour = 0
            
            if wake_ampm == 'pm' and wake_hour != 12:
                wake_hour += 12
            elif wake_ampm == 'am' and wake_hour == 12:
                wake_hour = 0
            
            sleep_time = f"{sleep_hour:02d}:{sleep_min:02d}"
            wake_time = f"{wake_hour:02d}:{wake_min:02d}"
        
        # If we have both times, calculate duration and log
        if sleep_time and wake_time:
            try:
                sleep_dt = datetime.strptime(sleep_time, "%H:%M")
                wake_dt = datetime.strptime(wake_time, "%H:%M")
                
                # Handle overnight sleep (wake time is next day)
                if wake_dt <= sleep_dt:
                    wake_dt += timedelta(days=1)
                
                duration = (wake_dt - sleep_dt).total_seconds() / 3600
                today = datetime.now().date().isoformat()
                
                db.insert_sleep_log(today, sleep_time, wake_time, duration)
                return f"Logged sleep: {sleep_time} to {wake_time} ({duration:.1f} hours)"
            except:
                pass
        
        # If we only have one time, check if we can get the other from latest sleep
        latest_sleep = db.get_latest_sleep()
        if latest_sleep:
            if sleep_time and not wake_time:
                # We have sleep time, use latest wake time as reference
                return f"Logged sleep time: {sleep_time}. Use 'up at [time]' to complete the entry."
            elif wake_time and not sleep_time:
                # We have wake time, use latest sleep time
                prev_sleep_time = latest_sleep.get('sleep_time', '')
                if prev_sleep_time:
                    try:
                        sleep_dt = datetime.strptime(prev_sleep_time, "%H:%M")
                        wake_dt = datetime.strptime(wake_time, "%H:%M")
                        if wake_dt <= sleep_dt:
                            wake_dt += timedelta(days=1)
                        duration = (wake_dt - sleep_dt).total_seconds() / 3600
                        today = datetime.now().date().isoformat()
                        db.insert_sleep_log(today, prev_sleep_time, wake_time, duration)
                        return f"Logged sleep: {prev_sleep_time} to {wake_time} ({duration:.1f} hours)"
                    except:
                        pass
        
        return "Couldn't parse sleep times. Try: 'slept at 1:30' and 'up at 8', or 'slept 1:30-8'"
    
    def handle_fact_storage(self, message, entities, phone_number=None):
        """Handle storing facts/information"""
        # Pattern: "WiFi password is duke-guest-2025", "locker code 4312", "parking spot B17"
        message_lower = message.lower()
        
        # Look for "is" or "=" pattern
        if ' is ' in message_lower:
            parts = message_lower.split(' is ', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Extract context if present (e.g., "home WiFi password")
                context = None
                context_keywords = ['home', 'work', 'campus', 'apartment', 'office']
                for ctx in context_keywords:
                    if ctx in key:
                        context = ctx
                        key = key.replace(ctx, '').strip()
                        break
                
                fact_id = db.insert_fact(key, value, context)
                return f"Stored: {key} = {value}"
        
        # Look for "spot" pattern (e.g., "parking spot B17")
        if ' spot ' in message_lower:
            parts = message_lower.split(' spot ', 1)
            if len(parts) == 2:
                key_prefix = parts[0].strip()
                value = parts[1].strip()
                key = f"{key_prefix} spot"
                fact_id = db.insert_fact(key, value)
                return f"Stored: {key} = {value}"
        
        # Look for number patterns (e.g., "locker code 4312")
        numbers = entities.get('numbers', [])
        if numbers:
            # Try to find what the number is for
            for word in message_lower.split():
                if word not in ['is', 'the', 'a', 'an', 'my', 'code', 'number']:
                    key = word
                    value = str(numbers[0])
                    fact_id = db.insert_fact(key, value)
                    return f"Stored: {key} = {value}"
        
        return "Couldn't parse fact. Try: 'WiFi password is duke-guest-2025' or 'locker code 4312'"
    
    def handle_fact_query(self, message, entities, phone_number=None):
        """Handle querying stored facts"""
        message_lower = message.lower()
        
        # Clear any pending fact query state when a new query comes in
        if phone_number and phone_number in self.pending_fact_query:
            del self.pending_fact_query[phone_number]
        
        # Check if user wants to list all facts
        list_keywords = ['list all', 'show all', 'all facts', 'all information', 'everything stored', 'all stored']
        if any(keyword in message_lower for keyword in list_keywords):
            all_facts = db.get_all_facts()
            if not all_facts:
                return "No facts stored yet."
            
            response_parts = [f"Stored facts ({len(all_facts)} total):"]
            for fact in all_facts:
                key = fact.get('key', '')
                value = fact.get('value', '')
                context = fact.get('context', '')
                if context:
                    response_parts.append(f"  • {key} ({context}): {value}")
                else:
                    response_parts.append(f"  • {key}: {value}")
            
            return '\n'.join(response_parts)
        
        # Check if user wants to delete a fact
        delete_keywords = ['delete', 'remove', 'forget', 'erase']
        if any(keyword in message_lower for keyword in delete_keywords):
            # Clear any pending fact deletion state when a new deletion request comes in
            if phone_number and phone_number in self.pending_fact_deletion:
                del self.pending_fact_deletion[phone_number]
            # Extract key from delete request
            for keyword in delete_keywords:
                if keyword in message_lower:
                    parts = message_lower.split(keyword, 1)
                    if len(parts) > 1:
                        key_phrase = parts[1].strip()
                        # Remove common words
                        key_words = [w for w in key_phrase.split() if w not in ['the', 'my', 'a', 'an']]
                        key = ' '.join(key_words)
                        
                        # Try to find and delete
                        matches = db.search_facts(key)
                        if matches:
                            # If multiple matches, ask user to pick one
                            if len(matches) > 1:
                                if phone_number:
                                    self.pending_fact_deletion[phone_number] = {
                                        'matches': matches,
                                        'key': key
                                    }
                                
                                response = f"Found {len(matches)} matches. Which one should I delete?\n"
                                for i, match in enumerate(matches[:5], 1):  # Limit to 5 options
                                    match_key = match.get('key', '')
                                    match_value = match.get('value', '')
                                    context = match.get('context', '')
                                    if context:
                                        response += f"{i}. {match_key} ({context}): {match_value}\n"
                                    else:
                                        response += f"{i}. {match_key}: {match_value}\n"
                                return response
                            else:
                                # Single match - delete it directly
                                fact_id = int(matches[0].get('id', 0))
                                if db.delete_fact(fact_id=fact_id):
                                    deleted_key = matches[0].get('key', '')
                                    return f"Deleted: {deleted_key}"
                                else:
                                    return f"Failed to delete fact"
                        
                        return f"Couldn't find '{key}' to delete"
            
            return "What fact would you like to delete? (e.g., 'delete WiFi password')"
        
        # Extract key from query (e.g., "what's the WiFi password" -> "wifi password")
        # Remove question words
        question_words = ['what', 'where', 'who', 'when', 'how', 'is', 'the', 'my', 's', 'what\'s']
        words = [w for w in message_lower.split() if w not in question_words]
        
        if not words:
            return "What information are you looking for?"
        
        # Try to find matching fact - try both the full query and individual keywords
        query = ' '.join(words)
        matches = db.search_facts(query)
        
        # If no matches, try searching with individual words
        if not matches:
            for word in words:
                matches = db.search_facts(word)
                if matches:
                    break
        
        if matches:
            # If multiple matches, ask user to pick one
            if len(matches) > 1:
                if phone_number:
                    self.pending_fact_query[phone_number] = {
                        'matches': matches,
                        'query': query
                    }
                
                response = f"Found {len(matches)} matches. Which one did you mean?\n"
                for i, match in enumerate(matches[:5], 1):  # Limit to 5 options
                    key = match.get('key', '')
                    value = match.get('value', '')
                    context = match.get('context', '')
                    if context:
                        response += f"{i}. {key} ({context}): {value}\n"
                    else:
                        response += f"{i}. {key}: {value}\n"
                return response
            else:
                # Single match - return it directly
                match = matches[0]
                key = match.get('key', '')
                value = match.get('value', '')
                context = match.get('context', '')
                
                if context:
                    return f"{key} ({context}): {value}"
                return f"{key}: {value}"
        
        return f"Couldn't find information about '{query}'"
    
    def handle_fact_query_selection(self, message, phone_number):
        """Handle user's selection from fact query matches"""
        if phone_number not in self.pending_fact_query:
            return None
        
        pending = self.pending_fact_query[phone_number]
        matches = pending['matches']
        
        # Parse selection (could be "1", "one", "first", etc.)
        message_lower = message.lower().strip()
        
        # Only handle if it looks like a selection (starts with a number)
        import re
        numbers = re.findall(r'\d+', message_lower)
        if numbers:
            selection = int(numbers[0])
            if 1 <= selection <= len(matches):
                match = matches[selection - 1]
                
                # Remove from pending
                del self.pending_fact_query[phone_number]
                
                # Return the selected fact
                key = match.get('key', '')
                value = match.get('value', '')
                context = match.get('context', '')
                
                if context:
                    return f"{key} ({context}): {value}"
                return f"{key}: {value}"
        
        # If it doesn't look like a selection, return None to allow normal processing
        # This clears the pending state so the new query can be processed
        del self.pending_fact_query[phone_number]
        return None
    
    def handle_fact_deletion_selection(self, message, phone_number):
        """Handle user's selection from fact deletion matches"""
        if phone_number not in self.pending_fact_deletion:
            return None
        
        pending = self.pending_fact_deletion[phone_number]
        matches = pending['matches']
        
        # Parse selection (could be "1", "one", "first", etc.)
        message_lower = message.lower().strip()
        
        # Only handle if it looks like a selection (starts with a number)
        import re
        numbers = re.findall(r'\d+', message_lower)
        if numbers:
            selection = int(numbers[0])
            if 1 <= selection <= len(matches):
                match = matches[selection - 1]
                fact_id = int(match.get('id', 0))
                
                # Remove from pending
                del self.pending_fact_deletion[phone_number]
                
                # Delete the selected fact
                if db.delete_fact(fact_id=fact_id):
                    deleted_key = match.get('key', '')
                    return f"Deleted: {deleted_key}"
                else:
                    return f"Failed to delete fact"
        
        # If it doesn't look like a selection, return None to allow normal processing
        # This clears the pending state so the new query can be processed
        del self.pending_fact_deletion[phone_number]
        return None
    
    def handle_reschedule_response(self, message, phone_number):
        """Handle user's response to reschedule options"""
        if not hasattr(check_reminder_followups, 'pending_reschedules'):
            return None
    
        message_lower = message.lower().strip()
        
        # Find which reminder this might be for (check recent follow-ups)
        # For now, we'll check if message indicates completion or reschedule
        if any(word in message_lower for word in ['yes', 'done', 'completed', 'finished', 'did it']):
            # User completed the task - find the most recent reminder with follow-up
            all_reminders = db.get_reminders_todos(type='reminder', completed=False)
            for reminder in all_reminders:
                reminder_id = int(reminder.get('id', 0))
                if reminder_id in check_reminder_followups.pending_reschedules:
                    follow_up_sent = reminder.get('follow_up_sent', 'FALSE').upper() == 'TRUE'
                    if follow_up_sent:
                        # Mark as completed
                        db.update_reminder_todo(reminder_id, completed=True)
                        if reminder_id in check_reminder_followups.pending_reschedules:
                            del check_reminder_followups.pending_reschedules[reminder_id]
                        return f"Great! Marked '{reminder.get('content', '')}' as complete."
        
        # Check for reschedule selection (1, 2, etc.)
        import re
        numbers = re.findall(r'\d+', message_lower)
        if numbers:
            selection = int(numbers[0])
            # Find reminder with pending reschedule
            for reminder_id, options in check_reminder_followups.pending_reschedules.items():
                if 1 <= selection <= len(options):
                    selected_option = options[selection - 1]
                    new_due_date = selected_option['time']
                    
                    # Update reminder due date
                    reminder = None
                    all_reminders = db.get_reminders_todos(type='reminder', completed=False)
                    for r in all_reminders:
                        if int(r.get('id', 0)) == reminder_id:
                            reminder = r
                            break
                    
                    if reminder:
                        # We need to update the due_date - this requires reading and rewriting the CSV
                        db.update_reminder_due_date(reminder_id, new_due_date)
                        
                        # Remove from pending reschedules
                        del check_reminder_followups.pending_reschedules[reminder_id]
                        
                        content = reminder.get('content', '')
                        return f"Rescheduled '{content}' to {selected_option['text']}"
        
        # If message is "no" or "skip", just acknowledge
        if any(word in message_lower for word in ['no', 'skip', 'cancel', 'nope']):
            # Find and clear the pending reschedule
            for reminder_id in list(check_reminder_followups.pending_reschedules.keys()):
                if reminder_id in check_reminder_followups.pending_reschedules:
                    del check_reminder_followups.pending_reschedules[reminder_id]
                    return "Got it, I'll leave it as is."
        
        return None
    
    def fallback_response(self, message, phone_number=None):
        """Fallback response for unrecognized messages - tries to guess intent and asks for confirmation"""
        # Try to make an educated guess using NLP
        best_guess = self.nlp_processor.guess_intent(message)
        
        if best_guess and best_guess.get('confidence', 0) > 0.5:
            # We have a reasonable guess, but ask for confirmation instead of executing
            guessed_intent = best_guess.get('intent')
            guessed_reason = best_guess.get('reason', '')
            
            # Store pending confirmation if we have a phone number
            if phone_number:
                entities = self.nlp_processor.extract_entities(message)
                self.pending_confirmations[phone_number] = {
                    'intent': guessed_intent,
                    'message': message,
                    'entities': entities,
                    'reason': guessed_reason
                }
                return f"🤔 {guessed_reason}, is that correct?"
        
        # If no good guess or handling failed, provide simple message
        return "I didn't understand. Could you rephrase that?"
    
    def handle_confirmation(self, message, phone_number=None):
        """Handle confirmation responses (yes, yep, correct, no, etc.)"""
        message_lower = message.lower().strip()
        
        # Determine which phone number to use
        if phone_number is None:
            # Try to find phone number from pending confirmations
            # This handles explicit confirmation intents
            for pn, pending in self.pending_confirmations.items():
                phone_number = pn
                break
        
        if not phone_number or phone_number not in self.pending_confirmations:
            return None
        
        pending = self.pending_confirmations[phone_number]
        
        # Check if it's a positive confirmation
        positive_confirmations = ['yes', 'yep', 'yeah', 'yup', 'correct', 'right', 'that\'s right', 'that\'s correct', 
                                  'sure', 'ok', 'okay', 'confirm', 'confirmed', 'true', '1', 'yea']
        negative_confirmations = ['no', 'nope', 'nah', 'incorrect', 'wrong', 'false', '0', 'cancel']
        
        if any(confirm in message_lower for confirm in positive_confirmations):
            # User confirmed, execute the pending action
            intent = pending['intent']
            original_message = pending['message']
            entities = pending['entities']
            
            # Remove from pending
            del self.pending_confirmations[phone_number]
            
            # Execute the action
            response = self.handle_intent(intent, original_message, entities)
            if response:
                return response
            else:
                return "Action completed, but I couldn't generate a response."
        
        elif any(confirm in message_lower for confirm in negative_confirmations):
            # User declined, clear pending and ask what they meant
            del self.pending_confirmations[phone_number]
            return "Got it, I won't do that. What did you mean instead?"
        
        # If unclear, ask for clarification
        return "Please respond with 'yes' or 'no' to confirm or cancel."
    
    def _generate_suggestions(self, message):
        """Generate contextual suggestions based on message content"""
        message_lower = message.lower()
        
        # Check for keywords that might indicate what user wants
        if any(word in message_lower for word in ['water', 'drank', 'drink', 'bottle', 'hydration']):
            return "Did you mean to log water? Try: 'drank a bottle' or 'drank 500ml'"
        elif any(word in message_lower for word in ['ate', 'eat', 'food', 'meal', 'lunch', 'dinner', 'breakfast', 'snack']):
            return "Did you mean to log food? Try: 'ate pizza' or 'had a burger'"
        elif any(word in message_lower for word in ['gym', 'workout', 'exercise', 'lift', 'bench', 'squat', 'cardio']):
            return "Did you mean to log a workout? Try: 'did bench press 135x5'"
        elif any(word in message_lower for word in ['remind', 'reminder', 'remember', 'alert']):
            return "Did you mean to set a reminder? Try: 'remind me to call mom at 3pm'"
        elif any(word in message_lower for word in ['todo', 'task', 'need to', 'should', 'have to']):
            return "Did you mean to add a todo? Try: 'todo buy groceries'"
        elif any(word in message_lower for word in ['how much', 'how many', 'total', 'stats', 'summary', 'show me']):
            return "Did you mean to check your stats? Try: 'how much have I eaten' or 'show me my stats'"
        elif any(word in message_lower for word in ['done', 'finished', 'completed', 'did', 'called', 'went']):
            return "Did you mean to mark something complete? Try: 'called mom' or 'did groceries'"
        
        return "Could you rephrase that?"

# Routes
@app.route('/webhook/twilio', methods=['POST'])
@app.route('/sms', methods=['POST'])
def twilio_webhook():
    """Handle incoming SMS from Twilio using TwiML responses"""
    try:
        print(f"\n📱 === TWILIO WEBHOOK RECEIVED ===")
        
        # Extract SMS data from Twilio webhook (Twilio sends form data)
        from_number = request.form.get('From', '')
        to_number = request.form.get('To', '')
        message_body = request.form.get('Body', '')
        message_sid = request.form.get('MessageSid', '')
            
        print(f"📱 From: {from_number}")
        print(f"📱 To: {to_number}")
        print(f"📱 Message: {message_body}")
        print(f"📱 MessageSid: {message_sid}")
            
        if not message_body:
            print(f" Empty message body received")
            response = MessagingResponse()
            response.message("I didn't receive a message. Please try again.")
            return str(response), 200
        
        # Process the message
        print(f"Processing message...")
        processor = EnhancedMessageProcessor()
        response_text = processor.process_message(message_body, phone_number=from_number)
        
        print(f"NLP processing complete:")
        print(f"  Response: {response_text}")
        
        # Create TwiML response - Twilio will automatically send this back
        response = MessagingResponse()
        
        if response_text:
            # Limit message length (SMS has 1600 character limit, but we'll be safe)
            if len(response_text) > 1500:
                response_text = response_text[:1500] + "..."
            
            response.message(response_text)
            print(f"TwiML response created, Twilio will send automatically")
        else:
            response.message("I didn't understand that. Try sending 'help' for available commands.")
            print(f" No response generated, sending fallback")
        print(f"📱 === WEBHOOK PROCESSING COMPLETE ===\n")
        
        return str(response), 200
        
    except Exception as e:
        print(f"Error processing Twilio webhook: {e}")
        import traceback
        traceback.print_exc()
        # Return a TwiML error response
        response = MessagingResponse()
        response.message("Sorry, I encountered an error processing your message. Please try again.")
        return str(response), 200

@app.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """Legacy SMS webhook (kept for compatibility)"""
    message_body = request.form.get('Body', '')
    from_number = request.form.get('From', '')
    
    print(f"=== LEGACY SMS WEBHOOK ===")
    print(f"Message: '{message_body}'")
    print(f"From: '{from_number}'")
    print("===========================")
    
    # Process message
    processor = EnhancedMessageProcessor()
    response_text = processor.process_message(message_body)
    
    # For legacy webhook, return response in webhook format
    return jsonify({
        "response": response_text,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Health check endpoint for local testing"""
    try:
        print(f"\n🏥 === HEALTH CHECK REQUESTED ===")
        
        # Test database connection
        print(f"Testing CSV database...")
        print(f"Database directory: {config.DATABASE_DIR}")
        
        try:
            stats = db.get_stats()
            print(f"CSV database access successful")
            print(f"CSV files: food_logs.csv, water_logs.csv, gym_logs.csv, reminders_todos.csv")
            
            food_count = stats['food_logs']
            water_count = stats['water_logs']
            gym_count = stats['gym_logs']
            reminder_count = stats['reminders_todos']
            
            print(f"Database queries completed successfully")
            
        except Exception as db_error:
            print(f"Database error: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "error": f"Database error: {str(db_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Get communication service status
        print(f"Getting communication service status...")
        comm_status = communication_service.get_status()
        print(f"📱 Communication status: {comm_status}")
        
        response_data = {
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "service": "Alfred the Butler (Cloud)",
            "environment": "production",
            "communication": comm_status,
            "database_stats": {
                "food_logs": food_count,
                "water_logs": water_count,
                "gym_logs": gym_count,
                "reminders_todos": reminder_count,
            },
            "scheduled_jobs": [
                "Morning Check-in (every day)",
                "Reminder Checker (every 1m)",
                "Daily Database Dump (5:00 AM)"
            ]
        }
        
        print(f"Health check completed successfully")
        print(f"🏥 === HEALTH CHECK COMPLETE ===\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Health check error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500



def get_weather_summary():
    """Get current weather summary for morning check-in"""
    try:
        weather_api_key = os.getenv('WEATHER_API_KEY', '')
        weather_location = os.getenv('WEATHER_LOCATION', '')
        
        if not weather_api_key or not weather_location:
            return None
        
        # OpenWeatherMap API
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': weather_location,  # City name, e.g., "Durham,NC,US" or "New York"
            'appid': weather_api_key,
            'units': 'imperial'  # Use 'metric' for Celsius
        }
        
        response = requests.get(base_url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            temp = int(data['main']['temp'])
            description = data['weather'][0]['description'].capitalize()
            feels_like = int(data['main']['feels_like'])
            
            # Get weather emoji
            weather_code = data['weather'][0]['main']
            emoji_map = {
                'Clear': '☀️',
                'Clouds': '☁️',
                'Rain': '🌧️',
                'Drizzle': '🌦️',
                'Thunderstorm': '⛈️',
                'Snow': '❄️',
                'Mist': '🌫️',
                'Fog': '🌫️'
            }
            weather_emoji = emoji_map.get(weather_code, '🌤️')
            
            # Format weather summary
            if abs(temp - feels_like) > 3:
                return f"{weather_emoji} {temp}°F ({description}, feels like {feels_like}°F)"
            else:
                return f"{weather_emoji} {temp}°F, {description}"
        else:
            return None
    except Exception as e:
        print(f" Error fetching weather: {e}")
        return None

def get_streaks():
    """Calculate streaks for gym, water, and food logging"""
    streaks = {'gym': 0, 'water': 0, 'food': 0}
    today = datetime.now().date()
    
    try:
        # Gym streak
        gym_logs = db.get_gym_logs()
        if gym_logs:
            # Get unique dates with gym logs
            gym_dates = set()
            for log in gym_logs:
                try:
                    log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                    gym_dates.add(log_date)
                except:
                    pass
            
            # Calculate consecutive days from today backwards
            current_date = today
            while current_date in gym_dates:
                streaks['gym'] += 1
                current_date -= timedelta(days=1)
        
        # Water streak
        water_logs = db.get_water_logs()
        if water_logs:
            water_dates = set()
            for log in water_logs:
                try:
                    log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                    water_dates.add(log_date)
                except:
                    pass
            
            current_date = today
            while current_date in water_dates:
                streaks['water'] += 1
                current_date -= timedelta(days=1)
        
        # Food streak
        food_logs = db.get_food_logs()
        if food_logs:
            food_dates = set()
            for log in food_logs:
                try:
                    log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                    food_dates.add(log_date)
                except:
                    pass
            
            current_date = today
            while current_date in food_dates:
                streaks['food'] += 1
                current_date -= timedelta(days=1)
        
    except Exception as e:
        print(f" Error calculating streaks: {e}")
    
    return streaks

def get_daily_quote():
    """Get a daily motivational quote from API, ensuring no duplicates"""
    try:
        # Check if we already have a quote for today
        todays_quote = db.get_todays_quote()
        if todays_quote:
            quote_text = todays_quote['quote']
            author = todays_quote.get('author', '')
            if author:
                return f"{quote_text} - {author}"
            return quote_text
        
        # Get list of used quotes to avoid duplicates
        used_quotes = db.get_used_quotes()
        
        # Try to fetch a new quote from ZenQuotes API
        max_attempts = 10  # Try up to 10 times to find a new quote
        for attempt in range(max_attempts):
            try:
                # ZenQuotes API - free, no API key needed
                response = requests.get('https://zenquotes.io/api/today', timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        quote_text = data[0].get('q', '').strip()
                        author = data[0].get('a', '').strip()
                        
                        # Check if we've seen this quote before
                        if quote_text and quote_text not in used_quotes:
                            # Store this quote as used
                            db.add_used_quote(quote_text, author)
                            
                            # Format with author if available
                            if author:
                                return f"{quote_text} - {author}"
                            return quote_text
                
                # If API returned a duplicate or failed, try random quote endpoint
                response = requests.get('https://zenquotes.io/api/random', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        quote_text = data[0].get('q', '').strip()
                        author = data[0].get('a', '').strip()
                        
                        if quote_text and quote_text not in used_quotes:
                            db.add_used_quote(quote_text, author)
                            if author:
                                return f"{quote_text} - {author}"
                            return quote_text
                
            except Exception as e:
                print(f" Error fetching quote (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(0.5)  # Brief delay before retry
                continue
        
        # Fallback: If API fails or all quotes are duplicates, use local fallback
        print(" Could not fetch new quote from API, using fallback")
        fallback_quotes = [
            "The only bad workout is the one that didn't happen. ",
            "Progress, not perfection. 🌱",
            "You don't have to be great to start, but you have to start to be great. 🚀",
            "Your body can do it. It's your mind you need to convince. ",
            "Success is the sum of small efforts repeated day in and day out. 📈"
        ]
        # Use day of year for consistent daily selection if API fails
        day_of_year = datetime.now().timetuple().tm_yday
        random.seed(day_of_year + 1000)
        return random.choice(fallback_quotes)
        
    except Exception as e:
        print(f" Error in get_daily_quote: {e}")
        # Ultimate fallback
        return "Progress, not perfection. 🌱"

def get_todays_schedule():
    """Get today's reminders and calendar events for morning check-in"""
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        schedule_items = []
        
        # Get all reminders
        all_reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        for reminder in all_reminders:
            due_date_str = reminder.get('due_date', '')
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str).date()
                    if due_date == today:
                        # Format time
                        due_datetime = datetime.fromisoformat(due_date_str)
                        time_str = due_datetime.strftime("%I:%M %p")
                        schedule_items.append({
                            'time': time_str,
                            'content': reminder.get('content', ''),
                            'type': 'reminder'
                        })
                except:
                    pass
        
        # Get calendar events if calendar service is available
        # calendar_service is defined at module level
        try:
            from __main__ import calendar_service
        except ImportError:
            calendar_service = None
        
        if calendar_service:
            try:
                calendar_events = calendar_service.get_todays_events()
                for event in calendar_events:
                    summary = event.get('summary', 'No title')
                    start = event.get('start', {})
                    
                    if 'dateTime' in start:
                        # Has specific time
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        time_str = start_time.strftime("%I:%M %p")
                        schedule_items.append({
                            'time': time_str,
                            'content': summary,
                            'type': 'calendar'
                        })
                    elif 'date' in start:
                        # All-day event
                        schedule_items.append({
                            'time': 'All day',
                            'content': summary,
                            'type': 'calendar'
                        })
            except Exception as e:
                print(f" Error fetching calendar events for schedule: {e}")
        
        # Sort by time (all-day events first, then by time)
        schedule_items.sort(key=lambda x: (
            1 if x['time'] == 'All day' else 0,
            x['time'] if x['time'] != 'All day' else '23:59'
        ))
        
        return schedule_items
    except Exception as e:
        print(f" Error getting today's schedule: {e}")
        return []

def get_weekly_comparison():
    """Compare this week's stats vs last week's stats"""
    try:
        today = datetime.now().date()
        
        # Calculate week boundaries (Monday to Sunday)
        days_since_monday = today.weekday()
        this_week_start = today - timedelta(days=days_since_monday)
        this_week_end = this_week_start + timedelta(days=6)
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)
        
        # Get gym logs for both weeks
        all_gym_logs = db.get_gym_logs()
        this_week_gym = 0
        last_week_gym = 0
        
        for log in all_gym_logs:
            try:
                log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                if last_week_start <= log_date <= last_week_end:
                    last_week_gym += 1
                elif this_week_start <= log_date <= this_week_end:
                    this_week_gym += 1
            except:
                pass
        
        # Get water logs for both weeks
        all_water_logs = db.get_water_logs()
        this_week_water_ml = 0
        last_week_water_ml = 0
        
        for log in all_water_logs:
            try:
                log_date = datetime.fromisoformat(log.get('timestamp', '')).date()
                amount_ml = float(log.get('amount_ml', 0))
                if last_week_start <= log_date <= last_week_end:
                    last_week_water_ml += amount_ml
                elif this_week_start <= log_date <= this_week_end:
                    this_week_water_ml += amount_ml
            except:
                pass
        
        return {
            'gym': {'this_week': this_week_gym, 'last_week': last_week_gym},
            'water_ml': {'this_week': this_week_water_ml, 'last_week': last_week_water_ml}
        }
    except Exception as e:
        print(f"  Error calculating weekly comparison: {e}")
        return None

def get_day_context():
    """Get day of week context message"""
    weekday = datetime.now().weekday()  # 0 = Monday, 6 = Sunday
    
    if weekday == 0:
        return "Happy Monday! 🎯"
    elif weekday == 4:
        return "TGIF! "
    elif weekday >= 5:
        return "Happy Weekend! 🌈"
    else:
        return None  # No special message for Tue-Thu

def morning_checkin():
    """Daily 8am check-in"""
    try:
        # Get incomplete todos
        incomplete_todos = db.get_reminders_todos(type='todo', completed=False)
        
        # Get incomplete reminders from yesterday or earlier
        yesterday = datetime.now() - timedelta(days=1)
        incomplete_reminders = db.get_reminders_todos(
            type='reminder', 
            completed=False,
            due_before=yesterday
        )
        
        # Get last gym session
        gym_logs = db.get_gym_logs()
        last_gym = None
        if gym_logs:
            # Sort by timestamp descending
            gym_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            last_gym = gym_logs[0]
        
        # Get day of week for context
        weekday = datetime.now().weekday()  # 0 = Monday, 6 = Sunday
        
        # Varied morning greetings with day context - use day of year to ensure consistency per day
        if weekday == 0:  # Monday
            greetings = [
                "Good morning! Happy Monday! ☀️",
                "Rise and shine! It's Monday - let's start the week strong! ",
                "Morning! New week, new opportunities! 🚀",
                "Hey there! Monday motivation - you've got this! 🎯"
            ]
        elif weekday == 4:  # Friday
            greetings = [
                "Good morning! TGIF! ",
                "Rise and shine! It's Friday - almost there! 🌟",
                "Morning! Friday vibes - finish the week strong! ",
                "Hey! TGIF - let's make it a great day! 🎊"
            ]
        elif weekday >= 5:  # Weekend
            greetings = [
                "Good morning! It's the weekend! 🌈",
                "Rise and shine! Weekend vibes! ☀️",
                "Morning! Weekend time - enjoy it! 😊",
                "Hey! Weekend mode activated! "
            ]
        else:  # Tuesday-Thursday
            greetings = [
                "Good morning! ☀️",
                "Rise and shine! 🌅",
                "Morning! Let's make today great! ",
                "Hey there! Ready to tackle the day? 🚀",
                "Good morning! Hope you slept well! 😊",
                "Rise and grind! ☕",
                "Morning! Time to shine!",
                "Good morning! Another day, another opportunity! 🌟"
            ]
        
        # Use day of year as seed for consistent daily selection
        day_of_year = datetime.now().timetuple().tm_yday
        random.seed(day_of_year)
        greeting = random.choice(greetings)
        
        # Build message
        message_parts = [greeting]
        
        # Add weather if available
        weather_summary = get_weather_summary()
        if weather_summary:
            message_parts.append(f"🌤️ Weather: {weather_summary}")
        
        # Add streaks in natural language
        streaks = get_streaks()
        streak_messages = []
        
        if streaks['gym'] > 0:
            if streaks['gym'] == 1:
                streak_messages.append("You hit the gym yesterday!")
            elif streaks['gym'] < 7:
                streak_messages.append(f"You've been to the gym {streaks['gym']} days in a row now!")
            else:
                streak_messages.append(f"You're on a {streaks['gym']}-day gym streak - that's amazing! 🔥")
        
        if streaks['water'] > 0:
            if streaks['water'] == 1:
                streak_messages.append("You hit your water goal yesterday!")
            elif streaks['water'] < 7:
                streak_messages.append(f"You've hit your water goal for the past {streaks['water']} days!")
            else:
                streak_messages.append(f"You've hit your water goal for {streaks['water']} days straight - keep it up! ")
        
        if streaks['food'] > 0:
            if streaks['food'] == 1:
                streak_messages.append("You logged food yesterday!")
            elif streaks['food'] < 7:
                streak_messages.append(f"You've logged food for {streaks['food']} days in a row!")
            else:
                streak_messages.append(f"You're on a {streaks['food']}-day food logging streak! ")
        
        if streak_messages:
            # Combine related streaks naturally
            if len(streak_messages) >= 2 and streaks['gym'] > 0 and streaks['water'] > 0:
                # Combine gym and water streaks in one natural sentence
                gym_msg = streak_messages[0] if "gym" in streak_messages[0].lower() else [m for m in streak_messages if "gym" in m.lower()][0]
                water_msg = streak_messages[1] if "water" in streak_messages[1].lower() else [m for m in streak_messages if "water" in m.lower()][0]
                combined = f"{gym_msg} And {water_msg.lower()}"
                message_parts.append(combined)
                if len(streak_messages) > 2:
                    food_msg = [m for m in streak_messages if "food" in m.lower() or "logged" in m.lower()]
                    if food_msg:
                        message_parts.append(f"{food_msg[0]}")
            else:
                for msg in streak_messages:
                    emoji = ""if "gym" in msg.lower() else "" if "water" in msg.lower() else ""
                    message_parts.append(f"{emoji} {msg}")
        
        # Add today's schedule
        todays_schedule = get_todays_schedule()
        if todays_schedule:
            if len(todays_schedule) == 1:
                item = todays_schedule[0]
                message_parts.append(f" Today: {item['time']} - {item['content']}")
            else:
                has_calendar = any(i.get('type') == 'calendar' for i in todays_schedule)
                message_parts.append(f" Today: {len(todays_schedule)} {'items' if has_calendar else 'reminders'} scheduled")
                # Show first 2 items
                for item in todays_schedule[:2]:
                    message_parts.append(f"   • {item['time']}: {item['content']}")
        
        # Add incomplete items
        incomplete_items = []
        for todo in incomplete_todos:
            incomplete_items.append(todo.get('content', ''))
        for reminder in incomplete_reminders:
            incomplete_items.append(reminder.get('content', ''))
        
        if incomplete_items:
            items_text = ', '.join([f"{i+1}) {item}" for i, item in enumerate(incomplete_items)])
            message_parts.append(f"Unfinished: {items_text}")
        
        # Add gym accountability in natural language
        if last_gym and streaks['gym'] == 0:  # Only show if not on a current streak
            last_timestamp = last_gym.get('timestamp', '')
            if last_timestamp:
                try:
                    last_date = datetime.fromisoformat(last_timestamp).date()
                    days_since = (datetime.now().date() - last_date).days
                    exercise = last_gym.get('exercise', 'workout')
                    
                    # Extract muscle group or exercise name for natural language
                    exercise_name = exercise
                    if ' - ' in exercise:
                        parts = exercise.split(' - ')
                        muscle_group = parts[0].lower()
                        exercise_name = parts[1] if len(parts) > 1 else exercise
                    elif 'chest' in exercise.lower():
                        muscle_group = "chest"
                    elif 'back' in exercise.lower():
                        muscle_group = "back"
                    elif 'legs' in exercise.lower() or 'leg' in exercise.lower():
                        muscle_group = "legs"
                    elif 'arms' in exercise.lower() or 'arm' in exercise.lower():
                        muscle_group = "arms"
                    elif 'shoulders' in exercise.lower() or 'shoulder' in exercise.lower():
                        muscle_group = "shoulders"
                    else:
                        muscle_group = None
                    
                    if days_since == 1:
                        message_parts.append(f"You hit {muscle_group if muscle_group else 'the gym'} yesterday - great job!")
                    elif days_since == 2:
                        if muscle_group:
                            message_parts.append(f"You hit {muscle_group} {days_since} days ago - how about hitting a lift today?")
                        else:
                            message_parts.append(f"You worked out {days_since} days ago - time for another session?")
                    elif days_since == 3:
                        if muscle_group:
                            message_parts.append(f"It's been {days_since} days since you hit {muscle_group} - ready to get back at it?")
                        else:
                            message_parts.append(f"It's been {days_since} days since your last workout - let's get moving!")
                    elif days_since >= 4:
                        if muscle_group:
                            message_parts.append(f"It's been {days_since} days since you hit {muscle_group} - time to get back in the gym!")
                        else:
                            message_parts.append(f"It's been {days_since} days since your last workout - let's get back on track!")
                except:
                    pass
        
        # Add daily quote
        quote = get_daily_quote()
        message_parts.append(f"\n💭 {quote}")
        
        # Always add water/outside reminder
        message_parts.append("Don't forget to drink water & keep smiling! 😁")
        
        # Send morning check-in via communication service
        user_phone = config.YOUR_PHONE_NUMBER
        message = '\n'.join(message_parts)
        if user_phone:
            communication_service.send_response(message, user_phone)
        else:
            print(f" No phone number configured for morning check-in")
        
    except Exception as e:
        print(f"Error in morning check-in: {e}")

def check_pending_reminders():
    """Check for pending reminders every minute (handled by check_reminders)"""
    # This function is now handled by check_reminders() which uses the reminders_todos table
    pass

# Old Gmail SMS checking function removed - now using Twilio webhooks

# Initialize the scheduler (after all functions are defined)
scheduler = BackgroundScheduler(
    job_defaults={
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 15
    }
)

# Add jobs to scheduler
scheduler.add_job(
    func=morning_checkin,
    trigger='cron',
    hour=config.MORNING_CHECKIN_HOUR,
    id='morning_checkin',
    name='Morning Check-in',
    replace_existing=True
)

scheduler.add_job(
    func=check_reminders,
    trigger=IntervalTrigger(minutes=1),
    id='check_reminders',
    name='Reminder Checker',
    replace_existing=True
)

scheduler.add_job(
    func=check_reminder_followups,
    trigger=IntervalTrigger(minutes=5),
    id='reminder_followup_checker',
    name='Reminder Follow-up Checker (every 5m)',
    replace_existing=True
)

# Add task decay checker (runs daily at 9 AM)
scheduler.add_job(
    func=check_task_decay,
    trigger='cron',
    hour=9,
    minute=0,
    id='task_decay_checker',
    name='Task Decay Checker (daily at 9 AM)',
    replace_existing=True
)

# Add weekly digest (runs on configured day and hour)
scheduler.add_job(
    func=send_weekly_digest,
    trigger='cron',
    day_of_week=config.WEEKLY_DIGEST_DAY,
    hour=config.WEEKLY_DIGEST_HOUR,
    id='weekly_digest',
    name='Weekly SMS Digest',
    replace_existing=True
)

# Add gentle nudges checker (runs every configured interval)
scheduler.add_job(
    func=check_gentle_nudges,
    trigger=IntervalTrigger(hours=config.GENTLE_NUDGE_CHECK_INTERVAL_HOURS),
    id='gentle_nudges_checker',
    name='Gentle Nudges Checker',
    replace_existing=True
)

scheduler.add_job(
    func=daily_database_dump,
    trigger='cron',
    hour=5,
    id='daily_dump',
    name='Daily Database Dump',
    replace_existing=True
)

# Cleanup - only register if not running tests
if os.getenv('RUNNING_TESTS') != '1':
    atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    # Check if another instance is already running
    if not check_single_instance():
        exit(1)
    
    # Get port from environment (for cloud deployment) or use default
    port = int(os.getenv('PORT', 5001))
    # Use 0.0.0.0 for cloud deployments (Render, Koyeb, etc.) or localhost for local dev
    host = '0.0.0.0' if os.getenv('RENDER') or os.getenv('KOYEB') or os.getenv('PORT') else 'localhost'
    
    print(f"🚀 Starting Alfred the Butler on {host}:{port}")
    print(f"🌐 Health check: http://{host}:{port}/health")
    print(f"📱 Twilio webhook: http://{host}:{port}/webhook/twilio or /sms")
    
    # Start the scheduler (only if not running tests)
    if os.getenv('RUNNING_TESTS') != '1':
        scheduler.start()
        print("Background scheduler started")
    
    # Start the Flask app (only if not running tests)
    if os.getenv('RUNNING_TESTS') != '1':
        app.run(host=host, port=port, debug=False)
