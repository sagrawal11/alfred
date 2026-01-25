"""
SMS Assistant - Main Application
Refactored to use new modular architecture
"""

import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client, Client

from config import Config
from core.processor import MessageProcessor
from communication_service import CommunicationService
from web import AuthManager, DashboardData, register_web_routes
from web.integrations import register_integration_routes
from integrations import IntegrationAuthManager, SyncManager, WebhookHandler
from data import IntegrationRepository
from services import JobScheduler, ReminderService, SyncService, NotificationService
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

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

# Initialize web components
auth_manager = AuthManager(supabase)
dashboard_data = DashboardData(supabase)

# Initialize integration components
integration_repo = IntegrationRepository(supabase)
integration_auth = IntegrationAuthManager(supabase, integration_repo)
sync_manager = SyncManager(supabase, integration_repo, integration_auth)

# Register web routes
register_web_routes(app, supabase, auth_manager, dashboard_data)

# Register integration routes
register_integration_routes(app, supabase, auth_manager, integration_repo,
                           integration_auth, sync_manager)

# Initialize webhook handler
webhook_handler = WebhookHandler(integration_repo, sync_manager)

# Initialize background services
job_scheduler = JobScheduler(config)
reminder_service = ReminderService(supabase, config, communication_service)
sync_service = SyncService(supabase, config, sync_manager)
notification_service = NotificationService(supabase, config, communication_service)


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
    """Health check endpoint (basic)"""
    try:
        # Test database connection
        result = supabase.table('users').select('id').limit(1).execute()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "scheduler": "running" if job_scheduler.is_running() else "stopped"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/health/ready')
def health_ready():
    """Readiness check endpoint (for Kubernetes/load balancers)"""
    try:
        # Check database connection
        supabase.table('users').select('id').limit(1).execute()
        
        # Check scheduler is running
        if not job_scheduler.is_running():
            return jsonify({
                "status": "not_ready",
                "reason": "scheduler_not_running",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        return jsonify({
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/health/live')
def health_live():
    """Liveness check endpoint (for Kubernetes)"""
    # Simple check - if Flask is responding, we're alive
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }), 200


# ============================================================================
# Integration Webhook Routes
# ============================================================================

@app.route('/webhook/fitbit', methods=['GET', 'POST'])
def fitbit_webhook():
    """Handle Fitbit webhooks"""
    result = webhook_handler.handle_fitbit_webhook(request)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result), 200

@app.route('/webhook/google/<provider>', methods=['POST'])
def google_webhook(provider: str):
    """Handle Google webhooks (Calendar, Fit, etc.)"""
    result = webhook_handler.handle_google_webhook(request, provider)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result), 200


# ============================================================================
# Background Job Scheduler
# ============================================================================

def setup_scheduled_jobs():
    """Configure all scheduled background jobs"""
    # Start scheduler
    job_scheduler.start()
    
    # Reminder follow-ups - check every 5 minutes
    job_scheduler.add_job(
        func=reminder_service.check_reminder_followups,
        trigger=IntervalTrigger(minutes=5),
        id='reminder_followups'
    )
    
    # Task decay checks - check every 6 hours
    job_scheduler.add_job(
        func=reminder_service.check_task_decay,
        trigger=IntervalTrigger(hours=6),
        id='task_decay'
    )
    
    # Gentle nudges - check every 2 hours
    if config.GENTLE_NUDGES_ENABLED:
        job_scheduler.add_job(
            func=notification_service.check_gentle_nudges,
            trigger=IntervalTrigger(hours=config.GENTLE_NUDGE_CHECK_INTERVAL_HOURS),
            id='gentle_nudges'
        )
    
    # Weekly digest - send on Monday at configured hour
    if config.WEEKLY_DIGEST_ENABLED:
        job_scheduler.add_job(
            func=notification_service.send_weekly_digest,
            trigger=CronTrigger(day_of_week=config.WEEKLY_DIGEST_DAY, hour=config.WEEKLY_DIGEST_HOUR),
            id='weekly_digest'
        )
    
    # Integration syncs - sync every 4 hours
    job_scheduler.add_job(
        func=sync_service.sync_all_integrations,
        trigger=IntervalTrigger(hours=4),
        id='integration_sync'
    )
    
    print("✅ Background jobs scheduled")

# Setup scheduled jobs
setup_scheduled_jobs()

# Cleanup on exit
import atexit
atexit.register(lambda: job_scheduler.shutdown(wait=True))


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    print("=" * 60)
    print("SMS Assistant - Starting...")
    print("=" * 60)
    print(f"Supabase URL: {config.SUPABASE_URL[:30]}...")
    print(f"Twilio configured: {bool(config.TWILIO_ACCOUNT_SID)}")
    print(f"Dashboard: http://localhost:{port}/dashboard/login")
    print("=" * 60)
    
    # Run Flask app (default 5001 to avoid port 5000 / AirPlay on macOS)
    app.run(host='0.0.0.0', port=port, debug=True)
