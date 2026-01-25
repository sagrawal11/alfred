"""
SMS Assistant - Main Application
Refactored to use new modular architecture
"""

import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client, Client

from config import Config
from core.processor import MessageProcessor
from communication_service import CommunicationService

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize configuration
config = Config()
if not config.SUPABASE_URL or not config.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Initialize Supabase
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Initialize services
communication_service = CommunicationService()

# Initialize message processor (singleton)
message_processor: MessageProcessor = None

def get_message_processor() -> MessageProcessor:
    """Get or create message processor instance"""
    global message_processor
    if message_processor is None:
        message_processor = MessageProcessor(supabase)
    return message_processor


# ============================================================================
# Twilio Webhook Routes
# ============================================================================

@app.route('/webhook/twilio', methods=['POST'])
@app.route('/sms', methods=['POST'])
def twilio_webhook():
    """Handle incoming SMS from Twilio"""
    try:
        print(f"\n📱 === TWILIO WEBHOOK RECEIVED ===")
        
        # Extract SMS data
        from_number = request.form.get('From', '')
        to_number = request.form.get('To', '')
        message_body = request.form.get('Body', '')
        message_sid = request.form.get('MessageSid', '')
        
        print(f"📱 From: {from_number}")
        print(f"📱 Message: {message_body}")
        
        if not message_body:
            response = MessagingResponse()
            response.message("I didn't receive a message. Please try again.")
            return str(response), 200
        
        # Process message
        processor = get_message_processor()
        response_text = processor.process_message(message_body, phone_number=from_number)
        
        print(f"📱 Response: {response_text}")
        
        # Create TwiML response
        response = MessagingResponse()
        
        if response_text:
            # Limit message length
            if len(response_text) > 1500:
                response_text = response_text[:1500] + "..."
            response.message(response_text)
        else:
            response.message("I didn't understand that. Try sending 'help' for available commands.")
        
        print(f"📱 === WEBHOOK PROCESSING COMPLETE ===\n")
        return str(response), 200
        
    except Exception as e:
        print(f"Error processing Twilio webhook: {e}")
        import traceback
        traceback.print_exc()
        response = MessagingResponse()
        response.message("Sorry, I encountered an error processing your message. Please try again.")
        return str(response), 200


@app.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """Legacy SMS webhook (kept for compatibility)"""
    message_body = request.form.get('Body', '')
    from_number = request.form.get('From', '')
    
    processor = get_message_processor()
    response_text = processor.process_message(message_body, phone_number=from_number)
    
    return jsonify({
        "response": response_text,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================================
# Health Check
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = supabase.table('users').select('id').limit(1).execute()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# ============================================================================
# Scheduler (for reminders, nudges, etc.)
# ============================================================================

def check_reminders():
    """Check and send reminders (placeholder - to be implemented in Phase 5)"""
    # TODO: Implement reminder checking
    pass

def check_gentle_nudges():
    """Check and send gentle nudges (placeholder - to be implemented in Phase 5)"""
    # TODO: Implement gentle nudges
    pass

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Schedule tasks (to be configured in Phase 5)
# scheduler.add_job(check_reminders, 'interval', minutes=5)
# scheduler.add_job(check_gentle_nudges, 'cron', hour=20)  # 8 PM daily

# Cleanup on exit
import atexit
atexit.register(lambda: scheduler.shutdown())


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SMS Assistant - Starting...")
    print("=" * 60)
    print(f"Supabase URL: {config.SUPABASE_URL[:30]}...")
    print(f"Twilio configured: {bool(config.TWILIO_ACCOUNT_SID)}")
    print("=" * 60)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
