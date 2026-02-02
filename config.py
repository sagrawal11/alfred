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
    
    # NLP Engine Selection
    # Default: openai (Gemini remains available as fallback)
    NLP_ENGINE = os.getenv('NLP_ENGINE', 'openai')  # 'openai' or 'gemini'
    
    # OpenAI Configuration (primary)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    
    # Google Gemini Configuration (fallback)
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

    # Base URL (used for OAuth redirects + Stripe success/cancel URLs)
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5001")
    
    # Dashboard Configuration
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', '')
    
    # Flask Security Configuration
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '')
    
    # Token Encryption (for OAuth tokens)
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')
    
    # Integration OAuth Configuration
    FITBIT_CLIENT_ID = os.getenv('FITBIT_CLIENT_ID', '')
    FITBIT_CLIENT_SECRET = os.getenv('FITBIT_CLIENT_SECRET', '')
    
    # Redis Configuration (optional - for caching)
    REDIS_URL = os.getenv('REDIS_URL', '')

    # Stripe (payments)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_CORE_MONTHLY = os.getenv("STRIPE_PRICE_CORE_MONTHLY", "")
    STRIPE_PRICE_CORE_ANNUAL = os.getenv("STRIPE_PRICE_CORE_ANNUAL", "")
    STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
    STRIPE_PRICE_PRO_ANNUAL = os.getenv("STRIPE_PRICE_PRO_ANNUAL", "")

    # Nutrition / Food APIs (Milestone A)
    USDA_FDC_API_KEY = os.getenv("USDA_FDC_API_KEY", "")
    OPENFOODFACTS_BASE_URL = os.getenv("OPENFOODFACTS_BASE_URL", "https://world.openfoodfacts.org")
    NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID", "")
    NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY", "")
    NUTRITION_CACHE_TTL_DAYS = int(os.getenv("NUTRITION_CACHE_TTL_DAYS", 30))

    # Dashboard uploads (Milestone B)
    FOOD_IMAGE_BUCKET = os.getenv("FOOD_IMAGE_BUCKET", "food-uploads")
    FOOD_IMAGE_MAX_BYTES = int(os.getenv("FOOD_IMAGE_MAX_BYTES", 6_000_000))  # ~6MB
    
    # Email Configuration (for password reset)
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', '')
    
    # Environment Configuration
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')  # 'development' or 'production'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    
    # Database (CSV files) - kept for backward compatibility if needed
    # config.py is in project root, so just use dirname once
    DATABASE_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'logs'
    )
    
    # Food Database (legacy - now loads all restaurant JSON files automatically)
    # Individual restaurant files are in data/ directory (e.g., sazon.json, ginger_and_soy.json)
    # The system automatically loads all *.json files from data/ excluding snacks.json, gym_workouts.json
    FOOD_DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'wu_foods.json'  # Kept for backward compatibility/fallback
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
