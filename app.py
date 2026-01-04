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
from csv_database import CSVDatabase

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
        print("❌ Another instance is already running on port 5001")
        print("   Please stop the other instance first")
        return False

def daily_database_dump():
    """Archive old logs (CSV files are already the archive, so just clean old entries)"""
    try:
        print("🔄 Starting daily database cleanup at 5 AM...")
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Delete logs older than today (keep only today's logs)
        db.delete_old_logs(today)
        
        print(f"✅ Daily database cleanup completed! Kept logs from {today} onwards")
        
    except Exception as e:
        print(f"❌ Error during daily database cleanup: {e}")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize services
communication_service = CommunicationService()

# Load configuration
config = Config()

# Initialize CSV database
db = CSVDatabase(config.DATABASE_DIR)

# Validate configuration
try:
    config.validate()
    print("✅ Configuration validated successfully")
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set")
    exit(1)

# Ensure required directories exist
def ensure_directories():
    """Create required directories if they don't exist"""
    try:
        # Debug: Show current working directory
        print(f"🔍 Current working directory: {os.getcwd()}")
        print(f"🔍 __file__ location: {__file__}")
        print(f"🔍 Absolute file path: {os.path.abspath(__file__)}")
        
        # Create database directory (for CSV files)
        print(f"🔍 Database directory path: {config.DATABASE_DIR}")
        os.makedirs(config.DATABASE_DIR, exist_ok=True)
        print(f"✅ Database directory ensured: {config.DATABASE_DIR}")
        
        # Create data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        print(f"🔍 Data directory path: {data_dir}")
        os.makedirs(data_dir, exist_ok=True)
        print(f"✅ Data directory ensured: {data_dir}")
        
        # Check if CSV files exist
        csv_files = ['food_logs.csv', 'water_logs.csv', 'gym_logs.csv', 'reminders_todos.csv']
        for csv_file in csv_files:
            csv_path = os.path.join(config.DATABASE_DIR, csv_file)
            if os.path.exists(csv_path):
                size = os.path.getsize(csv_path)
                print(f"✅ {csv_file} exists: {size} bytes")
        else:
                print(f"📝 {csv_file} will be created on first use")
            
        if os.path.exists(config.FOOD_DATABASE_PATH):
            print(f"✅ Food database exists: {config.FOOD_DATABASE_PATH}")
            size = os.path.getsize(config.FOOD_DATABASE_PATH)
            print(f"📊 Food database size: {size} bytes")
        else:
            print(f"❌ Food database missing: {config.FOOD_DATABASE_PATH}")
        
        # List contents of key directories
        print(f"\n📁 Contents of project root:")
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if os.path.exists(project_root):
                for item in os.listdir(project_root):
                    item_path = os.path.join(project_root, item)
                    if os.path.isdir(item_path):
                        print(f"   📁 {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        print(f"   📄 {item} ({size} bytes)")
            else:
                print(f"   ❌ Project root not found: {project_root}")
        except Exception as e:
            print(f"   ⚠️  Error listing project root: {e}")
        
        print(f"\n📁 Contents of database directory (CSV files):")
        try:
            if os.path.exists(config.DATABASE_DIR):
                for item in os.listdir(config.DATABASE_DIR):
                    item_path = os.path.join(config.DATABASE_DIR, item)
                    if os.path.isdir(item_path):
                        print(f"   📁 {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        print(f"   📄 {item} ({size} bytes)")
            else:
                print(f"   ❌ Database directory not found: {config.DATABASE_DIR}")
        except Exception as e:
            print(f"   ⚠️  Error listing database directory: {e}")
        
        print(f"\n📁 Contents of data directory:")
        try:
            if os.path.exists(data_dir):
                for item in os.listdir(data_dir):
                    item_path = os.path.join(data_dir, item)
                    if os.path.isdir(item_path):
                        print(f"   📁 {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        print(f"   📄 {item} ({size} bytes)")
            else:
                print(f"   ❌ Data directory not found: {data_dir}")
        except Exception as e:
            print(f"   ⚠️  Error listing data directory: {e}")
        
    except Exception as e:
        print(f"⚠️  Error creating directories: {e}")
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
        
        # Get all due reminders that haven't been sent
        due_reminders = db.get_reminders_todos(
            type='reminder',
            completed=False,
            due_before=current_time
        )
        
        for reminder in due_reminders:
            reminder_id = int(reminder.get('id', 0))
            content = reminder.get('content', '')
            
            # Send reminder via communication service
            user_phone = config.YOUR_PHONE_NUMBER
            message = f"⏰ REMINDER: {content}"
            
            if user_phone:
                result = communication_service.send_response(message, user_phone)
            else:
                result = communication_service.send_response(message)
            
            if result['success']:
                print(f"🔔 Reminder sent via {result['method']}: {content}")
                # Mark as completed
                db.update_reminder_todo(reminder_id, completed=True)
            else:
                print(f"❌ Failed to send reminder: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error checking reminders: {e}")

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
    print("✅ CSV database initialized (all CSV files ready)")

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
                print("✅ Custom food database loaded")
        except FileNotFoundError:
            print("⚠️  Custom food database not found, using default")
            custom_food_db = FOOD_DATABASE
        
        self.nlp_processor = create_gemini_processor(custom_food_db)
        # Store pending confirmations: {phone_number: {intent, message, entities, reason}}
        self.pending_confirmations = {}
    
    def process_message(self, message_body, phone_number=None):
        """Main message processing pipeline using intelligent NLP"""
        # Check if this is a confirmation response first
        if phone_number and phone_number in self.pending_confirmations:
            confirmation_response = self.handle_confirmation(message_body, phone_number)
            if confirmation_response:
                return confirmation_response
        
        # Use intelligent NLP processor to classify intent and extract entities
        intent = self.nlp_processor.classify_intent(message_body)
        entities = self.nlp_processor.extract_entities(message_body)
        
        print(f"🧠 Intelligent NLP Results:")
        print(f"   Intent: {intent}")
        print(f"   Entities: {entities}")
        
        # Process based on intent
        response = self.handle_intent(intent, message_body, entities)
        if response:
            return response
        
        return self.fallback_response(message_body, phone_number)
    
    def handle_intent(self, intent, message, entities):
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
        elif intent == 'confirmation':
            # Handle explicit confirmations (yes, yep, correct, etc.)
            return self.handle_confirmation(message, None)
        elif intent == 'unknown':
            return self.fallback_response(message, None)
        
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
            
            response = f"✅ Logged {bottle_text} of water ({amount_ml}ml)\n"
            response += f"💧 Total for today: {int(today_total_ml)}mL"
            
            if remaining_ml > 0:
                response += f"\n📊 Need about {bottles_needed} more {'bottle' if bottles_needed == 1 else 'bottles'} to hit your goal of {int(today_goal_ml)}mL today"
            else:
                response += f"\n🎉 You've hit your goal of {int(today_goal_ml)}mL today!"
            
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
                serving_info = f" ({food_info['serving_size']})" if 'serving_size' in food_info else ""
                food_display = food_name.replace('_', ' ').title() if food_name else "food"
                response = f"🍽️ Logged {food_display}{serving_info}\n"
                response += f"📊 This meal: {calories} cal, {protein}g protein, {carbs}g carbs, {fat}g fat\n"
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
                if ex['reps']:
                    detail = f"{ex['name']} {ex['weight']}x{ex['reps']}"
                    if ex['sets'] > 1:
                        detail += f"x{ex['sets']}"
                else:
                    detail = f"{ex['name']} {ex['weight']}"
                exercise_details.append(detail)
            
            response = f"💪 Logged {workout_data['muscle_group']} workout: {', '.join(exercise_details)}"
            return response
        
        return None
    
    def log_gym_workout(self, workout_data):
        """Log gym workout to database"""
        exercises = workout_data.get('exercises', [])
        if exercises:
            # Log first exercise (can be extended to log multiple)
            ex = exercises[0]
            exercise_name = f"{workout_data.get('muscle_group', 'workout')} - {ex.get('name', 'exercise')}"
            db.insert_gym_log(
                exercise=exercise_name,
                sets=ex.get('sets'),
                reps=ex.get('reps'),
                weight=ex.get('weight'),
                notes=json.dumps(workout_data.get('exercises', []))
            )
    
    def handle_todo(self, message, entities):
        """Handle todo creation using enhanced NLP processor"""
        tasks = entities.get('tasks', [])
        if tasks:
            task = tasks[0]
            self.add_todo(task)
            return f"✅ Added to todo list: {task}"
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
            
            response = f"⏰ Reminder set: {reminder_data['content']} on {date_str} at {time_str}"
            if reminder_data.get('priority') == 'high':
                response += " (URGENT)"
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
            response = f"💧 Water goal set for {date_display}: {goal_liters}L ({int(goal_ml)}mL)"
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
                response_parts.append(f"💧 Water: {water_liters:.1f}L ({int(water_total_ml)}mL, ~{bottles} bottles)")
                if water_total_ml >= water_goal_ml:
                    response_parts.append(f"   ✅ Goal reached! ({goal_liters:.1f}L)")
                else:
                    remaining = water_goal_ml - water_total_ml
                    remaining_liters = remaining / 1000
                    bottles_needed = int(round(remaining / config.WATER_BOTTLE_SIZE_ML))
                    response_parts.append(f"   📊 {remaining_liters:.1f}L remaining ({bottles_needed} bottles) to reach {goal_liters:.1f}L goal")
            else:
                response_parts.append(f"💧 Water: 0L (goal: {goal_liters:.1f}L)")
        
        # Get food stats if requested
        if query_data.get('food') or query_data.get('all'):
            food_totals = db.get_todays_food_totals(today)
            if food_totals['calories'] > 0:
                response_parts.append(f"🍽️ Food: {int(food_totals['calories'])} cal")
                response_parts.append(f"   📊 {food_totals['protein']:.1f}g protein, {food_totals['carbs']:.1f}g carbs, {food_totals['fat']:.1f}g fat")
            else:
                response_parts.append(f"🍽️ Food: No meals logged today")
        
        # Get gym stats if requested
        if query_data.get('gym') or query_data.get('all'):
            gym_logs = db.get_gym_logs(today)
            if gym_logs:
                response_parts.append(f"💪 Gym: {len(gym_logs)} workout{'s' if len(gym_logs) != 1 else ''} logged today")
            else:
                response_parts.append(f"💪 Gym: No workouts logged today")
        
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
                                todo_list.append(f"   {i}. {content} (today)")
                            else:
                                todo_list.append(f"   {i}. {content}")
                        except:
                            todo_list.append(f"   {i}. {content}")
                    else:
                        todo_list.append(f"   {i}. {content}")
                
                response_parts.append(f"📋 Todos ({len(today_todos)}):")
                response_parts.extend(todo_list)
                if len(today_todos) > 10:
                    response_parts.append(f"   ... and {len(today_todos) - 10} more")
            else:
                response_parts.append(f"📋 Todos: No todos for today")
        
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
                                reminder_list.append(f"   {i}. {content} at {time_str}")
                            else:
                                reminder_list.append(f"   {i}. {content} on {date_str} at {time_str}")
                        except:
                            reminder_list.append(f"   {i}. {content}")
                    else:
                        reminder_list.append(f"   {i}. {content}")
                
                response_parts.append(f"⏰ Reminders ({len(today_reminders)}):")
                response_parts.extend(reminder_list)
                if len(today_reminders) > 10:
                    response_parts.append(f"   ... and {len(today_reminders) - 10} more")
            else:
                response_parts.append(f"⏰ Reminders: No reminders for today")
        
        if response_parts:
            # Determine header based on what's being shown
            if query_data.get('todos') and not query_data.get('all') and not query_data.get('food') and not query_data.get('water') and not query_data.get('gym'):
                return "📋 Your Todos:\n" + "\n".join(response_parts)
            elif query_data.get('reminders') and not query_data.get('all') and not query_data.get('food') and not query_data.get('water') and not query_data.get('gym') and not query_data.get('todos'):
                return "⏰ Your Reminders:\n" + "\n".join(response_parts)
            else:
                return "📊 Today's Stats:\n" + "\n".join(response_parts)
        
        return "📊 No stats available for today"
    
    def handle_completion(self, message, entities):
        """Handle task/reminder completions"""
        # Try to match and complete tasks/reminders based on message content
        completed_item = self.mark_task_complete(message)
        if completed_item:
            item_type = completed_item.get('type', 'task')
            content = completed_item.get('content', 'item')
            if item_type == 'reminder':
                return f"✅ Reminder completed: {content}"
            else:
                return f"✅ Todo completed: {content}"
        return "✅ I couldn't find a matching task or reminder to mark as complete."
    
    def mark_task_complete(self, message):
        """Mark task/reminder as complete by matching message content"""
        message_lower = message.lower()
        
        # Get all incomplete todos and reminders
        todos = db.get_reminders_todos(type='todo', completed=False)
        reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        all_items = []
        for todo in todos:
            all_items.append({**todo, 'item_type': 'todo'})
        for reminder in reminders:
            all_items.append({**reminder, 'item_type': 'reminder'})
        
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
            return {
                'type': best_match.get('item_type', 'todo'),
                'content': best_match.get('content', '')
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
        
        # If no good guess or handling failed, provide helpful suggestions
        suggestions = self._generate_suggestions(message)
        return f"🤔 I'm not sure what you meant. {suggestions}\n\nTry:\n• 'drank a bottle' (water)\n• 'ate [food]' (food logging)\n• 'remind me to [task]' (reminders)\n• 'todo [task]' (todos)\n• 'did bench press 135x5' (gym workout)\n• 'how much have I eaten' (stats)"
    
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
                return "✅ Action completed, but I couldn't generate a response."
        
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
            print(f"⚠️  Empty message body received")
            response = MessagingResponse()
            response.message("I didn't receive a message. Please try again.")
            return str(response), 200
        
        # Process the message
        print(f"✅ Processing message...")
        processor = EnhancedMessageProcessor()
        response_text = processor.process_message(message_body, phone_number=from_number)
        
        print(f"🧠 NLP processing complete:")
        print(f"   Response: {response_text}")
        
        # Create TwiML response - Twilio will automatically send this back
        response = MessagingResponse()
        
        if response_text:
            # Limit message length (SMS has 1600 character limit, but we'll be safe)
            if len(response_text) > 1500:
                response_text = response_text[:1500] + "..."
            
            response.message(response_text)
            print(f"✅ TwiML response created, Twilio will send automatically")
        else:
            response.message("I didn't understand that. Try sending 'help' for available commands.")
            print(f"⚠️  No response generated, sending fallback")
        print(f"📱 === WEBHOOK PROCESSING COMPLETE ===\n")
        
        return str(response), 200
        
    except Exception as e:
        print(f"❌ Error processing Twilio webhook: {e}")
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
        print(f"🔍 Testing CSV database...")
        print(f"🔍 Database directory: {config.DATABASE_DIR}")
        
        try:
            stats = db.get_stats()
            print(f"✅ CSV database access successful")
            print(f"📊 CSV files: food_logs.csv, water_logs.csv, gym_logs.csv, reminders_todos.csv")
            
            food_count = stats['food_logs']
            water_count = stats['water_logs']
            gym_count = stats['gym_logs']
            reminder_count = stats['reminders_todos']
            
            print(f"✅ Database queries completed successfully")
            
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "error": f"Database error: {str(db_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Get communication service status
        print(f"🔍 Getting communication service status...")
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
        
        print(f"✅ Health check completed successfully")
        print(f"🏥 === HEALTH CHECK COMPLETE ===\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Health check error: {e}")
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
        print(f"⚠️  Error fetching weather: {e}")
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
        print(f"⚠️  Error calculating streaks: {e}")
    
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
                print(f"⚠️  Error fetching quote (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(0.5)  # Brief delay before retry
                continue
        
        # Fallback: If API fails or all quotes are duplicates, use local fallback
        print("⚠️  Could not fetch new quote from API, using fallback")
        fallback_quotes = [
            "The only bad workout is the one that didn't happen. 💪",
            "Progress, not perfection. 🌱",
            "You don't have to be great to start, but you have to start to be great. 🚀",
            "Your body can do it. It's your mind you need to convince. 🧠",
            "Success is the sum of small efforts repeated day in and day out. 📈"
        ]
        # Use day of year for consistent daily selection if API fails
        day_of_year = datetime.now().timetuple().tm_yday
        random.seed(day_of_year + 1000)
        return random.choice(fallback_quotes)
        
    except Exception as e:
        print(f"⚠️  Error in get_daily_quote: {e}")
        # Ultimate fallback
        return "Progress, not perfection. 🌱"

def get_todays_schedule():
    """Get reminders scheduled for today"""
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Get all reminders
        all_reminders = db.get_reminders_todos(type='reminder', completed=False)
        
        todays_reminders = []
        for reminder in all_reminders:
            due_date_str = reminder.get('due_date', '')
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str).date()
                    if due_date == today:
                        # Format time
                        due_datetime = datetime.fromisoformat(due_date_str)
                        time_str = due_datetime.strftime("%I:%M %p")
                        todays_reminders.append({
                            'time': time_str,
                            'content': reminder.get('content', '')
                        })
                except:
                    pass
        
        return todays_reminders
    except Exception as e:
        print(f"⚠️  Error getting today's schedule: {e}")
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
        print(f"⚠️  Error calculating weekly comparison: {e}")
        return None

def get_day_context():
    """Get day of week context message"""
    weekday = datetime.now().weekday()  # 0 = Monday, 6 = Sunday
    
    if weekday == 0:
        return "Happy Monday! 🎯"
    elif weekday == 4:
        return "TGIF! 🎉"
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
                "Rise and shine! It's Monday - let's start the week strong! 💪",
                "Morning! New week, new opportunities! 🚀",
                "Hey there! Monday motivation - you've got this! 🎯"
            ]
        elif weekday == 4:  # Friday
            greetings = [
                "Good morning! TGIF! 🎉",
                "Rise and shine! It's Friday - almost there! 🌟",
                "Morning! Friday vibes - finish the week strong! 💪",
                "Hey! TGIF - let's make it a great day! 🎊"
            ]
        elif weekday >= 5:  # Weekend
            greetings = [
                "Good morning! It's the weekend! 🌈",
                "Rise and shine! Weekend vibes! ☀️",
                "Morning! Weekend time - enjoy it! 😊",
                "Hey! Weekend mode activated! 🎉"
            ]
        else:  # Tuesday-Thursday
            greetings = [
                "Good morning! ☀️",
                "Rise and shine! 🌅",
                "Morning! Let's make today great! 💪",
                "Hey there! Ready to tackle the day? 🚀",
                "Good morning! Hope you slept well! 😊",
                "Rise and grind! ☕",
                "Morning! Time to shine! ✨",
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
                streak_messages.append(f"You've hit your water goal for {streaks['water']} days straight - keep it up! 💧")
        
        if streaks['food'] > 0:
            if streaks['food'] == 1:
                streak_messages.append("You logged food yesterday!")
            elif streaks['food'] < 7:
                streak_messages.append(f"You've logged food for {streaks['food']} days in a row!")
            else:
                streak_messages.append(f"You're on a {streaks['food']}-day food logging streak! 📊")
        
        if streak_messages:
            # Combine related streaks naturally
            if len(streak_messages) >= 2 and streaks['gym'] > 0 and streaks['water'] > 0:
                # Combine gym and water streaks in one natural sentence
                gym_msg = streak_messages[0] if "gym" in streak_messages[0].lower() else [m for m in streak_messages if "gym" in m.lower()][0]
                water_msg = streak_messages[1] if "water" in streak_messages[1].lower() else [m for m in streak_messages if "water" in m.lower()][0]
                combined = f"💪 {gym_msg} And {water_msg.lower()}"
                message_parts.append(combined)
                if len(streak_messages) > 2:
                    food_msg = [m for m in streak_messages if "food" in m.lower() or "logged" in m.lower()]
                    if food_msg:
                        message_parts.append(f"📊 {food_msg[0]}")
            else:
                for msg in streak_messages:
                    emoji = "💪" if "gym" in msg.lower() else "💧" if "water" in msg.lower() else "📊"
                    message_parts.append(f"{emoji} {msg}")
        
        # Add today's schedule
        todays_reminders = get_todays_schedule()
        if todays_reminders:
            if len(todays_reminders) == 1:
                reminder = todays_reminders[0]
                message_parts.append(f"📅 Today: {reminder['time']} - {reminder['content']}")
            else:
                message_parts.append(f"📅 Today: {len(todays_reminders)} reminders scheduled")
                # Show first 2 reminders
                for reminder in todays_reminders[:2]:
                    message_parts.append(f"   • {reminder['time']}: {reminder['content']}")
        
        # Add incomplete items
        incomplete_items = []
        for todo in incomplete_todos:
            incomplete_items.append(todo.get('content', ''))
        for reminder in incomplete_reminders:
            incomplete_items.append(reminder.get('content', ''))
        
        if incomplete_items:
            items_text = ', '.join([f"{i+1}) {item}" for i, item in enumerate(incomplete_items)])
            message_parts.append(f"📋 Unfinished: {items_text}")
        
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
                        message_parts.append(f"💪 You hit {muscle_group if muscle_group else 'the gym'} yesterday - great job!")
                    elif days_since == 2:
                        if muscle_group:
                            message_parts.append(f"💪 You hit {muscle_group} {days_since} days ago - how about hitting a lift today?")
                        else:
                            message_parts.append(f"💪 You worked out {days_since} days ago - time for another session?")
                    elif days_since == 3:
                        if muscle_group:
                            message_parts.append(f"💪 It's been {days_since} days since you hit {muscle_group} - ready to get back at it?")
                        else:
                            message_parts.append(f"💪 It's been {days_since} days since your last workout - let's get moving!")
                    elif days_since >= 4:
                        if muscle_group:
                            message_parts.append(f"💪 It's been {days_since} days since you hit {muscle_group} - time to get back in the gym!")
                        else:
                            message_parts.append(f"💪 It's been {days_since} days since your last workout - let's get back on track!")
                except:
                    pass
        
        # Add daily quote
        quote = get_daily_quote()
        message_parts.append(f"\n💭 {quote}")
        
        # Always add water/outside reminder
        message_parts.append("💧 Don't forget to drink water & keep smiling! 😁")
        
        # Send morning check-in via communication service
        user_phone = config.YOUR_PHONE_NUMBER
        message = '\n'.join(message_parts)
        if user_phone:
            communication_service.send_response(message, user_phone)
        else:
            print(f"⚠️  No phone number configured for morning check-in")
        
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
    func=daily_database_dump,
    trigger='cron',
    hour=5,
    id='daily_dump',
    name='Daily Database Dump',
    replace_existing=True
)

# Cleanup
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    # Check if another instance is already running
    if not check_single_instance():
        exit(1)
    
    # Get port from environment (for cloud deployment) or use default
    port = int(os.getenv('PORT', 5001))
    host = '0.0.0.0' if os.getenv('RENDER') else 'localhost'
    
    print(f"🚀 Starting Alfred the Butler on {host}:{port}")
    print(f"🌐 Health check: http://{host}:{port}/health")
    print(f"📱 Twilio webhook: http://{host}:{port}/webhook/twilio or /sms")
    
    # Start the scheduler
    scheduler.start()
    print("⏰ Background scheduler started")
    
    # Start the Flask app
    app.run(host=host, port=port, debug=False)
