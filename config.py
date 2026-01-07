import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Twilio Configuration (primary SMS)
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    
    # Your phone number (for scheduled reminders)
    YOUR_PHONE_NUMBER = os.getenv('YOUR_PHONE_NUMBER', '')
    
    # Communication Mode (using TwiML, so SMS is automatic)
    COMMUNICATION_MODE = os.getenv('COMMUNICATION_MODE', 'sms')  # 'sms' only
    
    # NLP Engine Selection (Gemini only)
    NLP_ENGINE = os.getenv('NLP_ENGINE', 'gemini')  # Always 'gemini'
    
    # Google Gemini Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # App Settings
    MORNING_CHECKIN_HOUR = int(os.getenv('MORNING_CHECKIN_HOUR', 8))
    EVENING_REMINDER_HOUR = int(os.getenv('EVENING_REMINDER_HOUR', 20))
    
    # Water Bottle Size (in milliliters)
    # Default: 710ml (standard water bottle)
    WATER_BOTTLE_SIZE_ML = int(os.getenv('WATER_BOTTLE_SIZE_ML', 710))
    
    # Default Daily Water Goal (in milliliters)
    # Default: 4000ml (4L per day)
    DEFAULT_WATER_GOAL_ML = int(os.getenv('DEFAULT_WATER_GOAL_ML', 4000))
    
    # Reminder Follow-up Settings
    REMINDER_FOLLOWUP_DELAY_MINUTES = int(os.getenv('REMINDER_FOLLOWUP_DELAY_MINUTES', 30))  # Check back after 30 minutes
    REMINDER_AUTO_RESCHEDULE_ENABLED = os.getenv('REMINDER_AUTO_RESCHEDULE_ENABLED', 'true').lower() == 'true'
    
    # Task Decay & Cleanup Settings
    TASK_DECAY_DAYS = int(os.getenv('TASK_DECAY_DAYS', 7))  # Check tasks older than 7 days
    TASK_DECAY_ENABLED = os.getenv('TASK_DECAY_ENABLED', 'true').lower() == 'true'
    
    # Weekly Digest Settings
    WEEKLY_DIGEST_DAY = int(os.getenv('WEEKLY_DIGEST_DAY', 0))  # 0 = Monday, 6 = Sunday
    WEEKLY_DIGEST_HOUR = int(os.getenv('WEEKLY_DIGEST_HOUR', 20))  # 8 PM
    WEEKLY_DIGEST_ENABLED = os.getenv('WEEKLY_DIGEST_ENABLED', 'true').lower() == 'true'
    
    # Gentle Nudges Settings
    GENTLE_NUDGES_ENABLED = os.getenv('GENTLE_NUDGES_ENABLED', 'true').lower() == 'true'
    GENTLE_NUDGE_CHECK_INTERVAL_HOURS = int(os.getenv('GENTLE_NUDGE_CHECK_INTERVAL_HOURS', 2))  # Check every 2 hours
    
    # Weather API Configuration (optional - for morning check-in)
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
    WEATHER_LOCATION = os.getenv('WEATHER_LOCATION', '')  # e.g., "Durham,NC,US" or "New York"
    
    # Google Calendar API Configuration (optional - for calendar integration)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN', '')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5001/auth/google/callback')
    
    # Supabase Database Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Dashboard Configuration
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', '')
    
    # Database (CSV files) - kept for backward compatibility if needed
    # config.py is in project root, so just use dirname once
    DATABASE_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'logs'
    )
    
    # Food Database
    FOOD_DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'wu_foods.json'
    )
    
    # Gym Workout Database
    GYM_DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'gym_workouts.json'
    )
    
    # Snacks Database
    SNACKS_DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'snacks.json'
    )
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = []
        
        # Check communication mode requirements
        if cls.COMMUNICATION_MODE == 'sms':
            required_vars.extend([
                'TWILIO_ACCOUNT_SID',
                'TWILIO_AUTH_TOKEN',
                'TWILIO_PHONE_NUMBER'
        ])
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        return True
