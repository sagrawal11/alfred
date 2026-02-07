"""
SMS Assistant - Main Application
Modular architecture: web dashboard, SMS processing, integrations, background jobs.
"""

import os
import sys
from datetime import datetime

from flask import Flask, request, jsonify
from supabase import create_client, Client
from twilio.twiml.messaging_response import MessagingResponse

from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from communication_service import CommunicationService
from core.processor import MessageProcessor
from data import IntegrationRepository, UserRepository
from integrations import IntegrationAuthManager, SyncManager, WebhookHandler
from services import JobScheduler, ReminderService, SyncService, NotificationService
from web import AuthManager, DashboardData, register_web_routes
from web.integrations import register_integration_routes
 

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Rate limiting (Milestone D)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def _rate_limit_key():
        # Prefer user_id when logged in (dashboard), else phone number (Twilio), else IP.
        try:
            from flask import session as flask_session  # type: ignore
            uid = flask_session.get("user_id")
            if uid:
                return f"user:{uid}"
        except Exception:
            pass
        try:
            from flask import request as flask_request  # type: ignore
            frm = (flask_request.form.get("From") or "").strip()
            if frm:
                return f"phone:{frm}"
        except Exception:
            pass
        return get_remote_address()

    limiter = Limiter(_rate_limit_key, app=app, default_limits=["200 per day", "60 per hour"])
except Exception:
    limiter = None

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

# Initialize agent orchestrator (singleton; enabled via env flag)
agent_orchestrator = None

def get_message_processor() -> MessageProcessor:
    """Get or create message processor instance"""
    global message_processor
    if message_processor is None:
        message_processor = MessageProcessor(supabase)
    return message_processor


def get_agent_orchestrator():
    """Get or create agent orchestrator instance (Option B)."""
    global agent_orchestrator
    if agent_orchestrator is None:
        from services.agent.orchestrator import AgentOrchestrator
        agent_orchestrator = AgentOrchestrator(supabase)
    return agent_orchestrator

# Initialize web components
auth_manager = AuthManager(supabase)
dashboard_data = DashboardData(supabase)

# Initialize integration components
integration_repo = IntegrationRepository(supabase)
integration_auth = IntegrationAuthManager(supabase, integration_repo)
sync_manager = SyncManager(supabase, integration_repo, integration_auth)

# Initialize background services (before registering routes that need them)
job_scheduler = JobScheduler(config)
reminder_service = ReminderService(supabase, config, communication_service)
sync_service = SyncService(supabase, config, sync_manager)
notification_service = NotificationService(supabase, config, communication_service)

# Register web routes
register_web_routes(app, supabase, auth_manager, dashboard_data,
                    job_scheduler, reminder_service, sync_service, notification_service, limiter=limiter,
                    get_message_processor_fn=get_message_processor,
                    get_agent_orchestrator_fn=get_agent_orchestrator)

# Register integration routes
register_integration_routes(app, supabase, auth_manager, integration_repo,
                           integration_auth, sync_manager)

# Initialize webhook handler
webhook_handler = WebhookHandler(integration_repo, sync_manager)


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

        if len((message_body or "").strip()) > 300:
            response = MessagingResponse()
            response.message("Message must be 300 characters or less.")
            return str(response), 200

        # Prefer agent for onboarded users when enabled; fall back to classic processor otherwise.
        response_text = None
        try:
            if os.getenv("AGENT_MODE_ENABLED", "true").lower() == "true":
                # Keep STOP/HELP/re-subscribe behavior aligned with classic processor.
                low = (message_body or "").strip().lower()
                _resubscribe = (
                    low in ("start", "hi alfred", "hey alfred", "hello alfred")
                    or (low.startswith("hi ") and "alfred" in low and len(low) < 30)
                    or (low.startswith("hey ") and "alfred" in low and len(low) < 30)
                )
                if low not in ("help", "info", "stop") and not _resubscribe:
                    user = UserRepository(supabase).get_by_phone(from_number)
                    if user and user.get("onboarding_complete", False):
                        quota_blocked = False
                        # Monthly quota enforcement (turns)
                        try:
                            from data import UserUsageRepository
                            plan = (user.get("plan") or "free").strip().lower()
                            month_key = UserUsageRepository.month_key_for()
                            # Conservative defaults; can be tuned in pricing tier work.
                            quota = 50 if plan == "free" else 1000 if plan == "core" else None
                            if quota is not None:
                                cur = supabase.table("user_usage_monthly").select("turns_used").eq("user_id", int(user["id"])).eq("month_key", month_key).limit(1).execute()
                                used = int((cur.data[0].get("turns_used") if cur.data else 0) or 0)
                                if used >= quota:
                                    response_text = [
                                        "You’ve hit your monthly message limit for this plan.",
                                        "Upgrade to Pro for unlimited messaging (with fair-use safeguards).",
                                    ]
                                    quota_blocked = True
                        except Exception as _quota_err:
                            # If quota exceeded we already set response_text; otherwise ignore quota errors.
                            if response_text:
                                pass
                        if not quota_blocked:
                            response_text = get_agent_orchestrator().handle_message(
                                user_id=int(user["id"]),
                                phone_number=str(from_number),
                                text=message_body,
                                source="sms",
                            )
                            # Count the turn after a successful agent call.
                            try:
                                from data import UserUsageRepository
                                UserUsageRepository(supabase).increment_month(int(user["id"]), UserUsageRepository.month_key_for(), delta=1)
                            except Exception:
                                pass
        except Exception:
            # Keep fallback behavior unless we already have a response.
            if response_text is None:
                response_text = None

        if response_text is None:
            processor = get_message_processor()
            response_text = processor.process_message(message_body, phone_number=from_number)
        
        print(f"📱 Response: {response_text}")
        
        # Create TwiML response
        response = MessagingResponse()
        
        # Support multi-message replies (used by onboarding to send a greeting + first question).
        parts = []
        if isinstance(response_text, (list, tuple)):
            parts = [p for p in response_text if p]
        elif response_text:
            parts = [response_text]

        if parts:
            for part in parts:
                if len(part) > 1500:
                    part = part[:1500] + "..."
                response.message(part)
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

    if len((message_body or "").strip()) > 300:
        return jsonify({"response": "Message must be 300 characters or less.", "timestamp": datetime.now().isoformat()})

    processor = get_message_processor()
    response_text = processor.process_message(message_body, phone_number=from_number)

    # Keep legacy endpoint shape stable (single string), but allow onboarding to return multi-part.
    if isinstance(response_text, (list, tuple)):
        response_text = "\n\n".join([p for p in response_text if p])
    
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

    # Morning check-in - evaluate due users periodically (per-user hour + timezone)
    job_scheduler.add_job(
        func=notification_service.send_morning_checkins_due,
        trigger=IntervalTrigger(minutes=15),
        id='morning_checkins'
    )
    
    # Weekly digest - evaluate due users periodically (per-user day/hour + timezone)
    if config.WEEKLY_DIGEST_ENABLED:
        job_scheduler.add_job(
            func=notification_service.send_weekly_digest_due,
            trigger=IntervalTrigger(minutes=30),
            id='weekly_digest_due'
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
    print(f"Homepage:  http://localhost:{port}/")
    print(f"Dashboard: http://localhost:{port}/dashboard/login  (redirects to homepage)")
    print("=" * 60)
    
    # Run Flask app (default 5001 to avoid port 5000 / AirPlay on macOS)
    app.run(host='0.0.0.0', port=port, debug=True)
