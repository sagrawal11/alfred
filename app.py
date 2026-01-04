import os
import sys
import json
import atexit
import csv
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
    
    def process_message(self, message_body):
        """Main message processing pipeline using intelligent NLP"""
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
        
        return self.fallback_response(message_body)
    
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
        elif intent == 'unknown':
            return self.fallback_response(message)
        
        return None
    
    def handle_water(self, message, entities):
        """Handle water logging using enhanced NLP processor"""
        amount_ml = self.nlp_processor.parse_water_amount(message, entities)
        if amount_ml:
            self.log_water(amount_ml)
            oz = round(amount_ml / 29.5735, 1)
            return f"✅ Logged {oz}oz water ({amount_ml}ml)"
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
                
                # Format response
                serving_info = f" ({food_info['serving_size']})" if 'serving_size' in food_info else ""
                food_display = food_name.replace('_', ' ').title() if food_name else "food"
                response = f"🍽️ Logged {food_display}{serving_info}\n"
                response += f"📊 Nutrition: {calories} cal, {protein}g protein, {carbs}g carbs, {fat}g fat"
                
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
    
    def handle_completion(self, message, entities):
        """Handle task/reminder completions"""
        completion_patterns = [
            'did', 'done', 'finished', 'completed', 'called', 'went'
        ]
        
        if any(pattern in message for pattern in completion_patterns):
            # Try to match and complete tasks/reminders
            self.mark_recent_task_complete(message)
            return "✅ Task marked as complete!"
        return None
    
    def mark_recent_task_complete(self, message):
        """Mark recent task as complete based on message content"""
        # Get most recent incomplete todo
        todos = db.get_reminders_todos(type='todo', completed=False)
        if todos:
            # Sort by timestamp descending and get most recent
            todos.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            most_recent = todos[0]
            item_id = int(most_recent.get('id', 0))
            db.update_reminder_todo(item_id, completed=True)
    
    def fallback_response(self, message):
        """Fallback response for unrecognized messages"""
        return "🤔 I didn't understand that. Try:\n• 'drank a bottle' (water)\n• 'ate [food]' (food logging)\n• 'remind me to [task]' (reminders)\n• 'todo [task]' (todos)\n• 'did bench press 135x5' (gym workout)"

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
        response_text = processor.process_message(message_body)
        
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
        
        # Varied morning greetings - use day of year to ensure consistency per day
        greetings = [
            "Good morning! ☀️",
            "Rise and shine! 🌅",
            "Morning! Let's make today great! 💪",
            "Hey there! Ready to tackle the day? 🚀",
            "Good morning! Hope you slept well! 😊",
            "Rise and grind! ☕",
            "Morning! Time to shine! ✨",
            "Good morning! Another day, another opportunity! 🌟",
            "Hey! Let's make today count! 📅",
            "Morning! You've got this! 💯",
            "Good morning! What's on the agenda today? 📋",
            "Rise and shine! Let's do this! 🔥",
            "Morning! Ready to crush your goals? 🎯",
            "Good morning! Make it a great one! 🌈",
            "Hey! Time to wake up and win! 🏆"
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
        
        # Add incomplete items
        incomplete_items = []
        for todo in incomplete_todos:
            incomplete_items.append(todo.get('content', ''))
        for reminder in incomplete_reminders:
            incomplete_items.append(reminder.get('content', ''))
        
        if incomplete_items:
            items_text = ', '.join([f"{i+1}) {item}" for i, item in enumerate(incomplete_items)])
            message_parts.append(f"📋 Unfinished: {items_text}")
        
        # Add gym accountability
        if last_gym:
            last_timestamp = last_gym.get('timestamp', '')
            if last_timestamp:
                try:
                    last_date = datetime.fromisoformat(last_timestamp).date()
                    days_since = (datetime.now().date() - last_date).days
                    exercise = last_gym.get('exercise', 'workout')
                    if days_since >= 2:
                        message_parts.append(f"Your last workout was {days_since} days ago ({exercise}) - time for next session?")
                except:
                    pass
        
        # Always add water/outside reminder
        message_parts.append("Don't forget to drink water & keep smiling!")
        
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
