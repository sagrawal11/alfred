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
    
    # Weather API Configuration (optional - for morning check-in)
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
    WEATHER_LOCATION = os.getenv('WEATHER_LOCATION', '')  # e.g., "Durham,NC,US" or "New York"
    
    # Database (CSV files)
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
