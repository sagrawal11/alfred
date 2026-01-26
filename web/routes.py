"""
Web Routes
Flask routes for dashboard and authentication
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
from typing import Callable

from .auth import AuthManager
from .dashboard import DashboardData


def register_web_routes(app: Flask, supabase, auth_manager: AuthManager, dashboard_data: DashboardData,
                        job_scheduler=None, reminder_service=None, sync_service=None, notification_service=None):
    """
    Register all web routes with the Flask app
    
    Args:
        app: Flask application instance
        supabase: Supabase client
        auth_manager: AuthManager instance
        dashboard_data: DashboardData instance
    """
    
    def require_login(f: Callable) -> Callable:
        """Decorator to require login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = auth_manager.require_auth()
            if not user:
                return redirect(url_for('dashboard_login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # ============================================================================
    # Landing Page Route
    # ============================================================================
    
    @app.route('/')
    def landing_page():
        """Landing page"""
        return render_template('index.html')
    
    # ============================================================================
    # Authentication Routes
    # ============================================================================
    
    @app.route('/dashboard/login', methods=['GET', 'POST'])
    def dashboard_login():
        """Login page"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                return render_template('dashboard/login.html', error='Email and password required')
            
            success, user, error = auth_manager.login(email, password)
            
            if success:
                return redirect(url_for('dashboard_index'))
            else:
                return render_template('dashboard/login.html', error=error or 'Login failed')
        
        # GET request - show login form
        return render_template('dashboard/login.html')
    
    @app.route('/dashboard/register', methods=['GET', 'POST'])
    def dashboard_register():
        """Registration page"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            name = request.form.get('name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            
            # Validation
            if not email or not password:
                return render_template('dashboard/register.html', error='Email and password required')
            
            if password != password_confirm:
                return render_template('dashboard/register.html', error='Passwords do not match')
            
            if len(password) < 8:
                return render_template('dashboard/register.html', error='Password must be at least 8 characters')
            
            # Register user
            success, user, error = auth_manager.register(email, password, name, phone_number)
            
            if success:
                # If phone number provided, send verification code
                if phone_number:
                    code_sent, code, error_msg = auth_manager.send_phone_verification_code(user['id'], phone_number)
                    if code_sent:
                        flash(f'Registration successful! Verification code sent to {phone_number}. Code: {code} (for testing)', 'success')
                        return redirect(url_for('dashboard_verify_phone'))
                    else:
                        flash(f'Registration successful, but failed to send verification code: {error_msg}', 'warning')
                else:
                    flash('Registration successful!', 'success')
                return redirect(url_for('dashboard_index'))
            else:
                return render_template('dashboard/register.html', error=error or 'Registration failed')
        
        # GET request - show registration form
        return render_template('dashboard/register.html')
    
    @app.route('/dashboard/verify-phone', methods=['GET', 'POST'])
    @require_login
    def dashboard_verify_phone():
        """Phone verification page"""
        user = auth_manager.get_current_user()
        
        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            
            if not code:
                return render_template('dashboard/verify_phone.html', error='Verification code required')
            
            success, error = auth_manager.verify_phone_code(user['id'], code)
            
            if success:
                flash('Phone number verified successfully!', 'success')
                return redirect(url_for('dashboard_index'))
            else:
                return render_template('dashboard/verify_phone.html', error=error or 'Verification failed')
        
        # GET request - show verification form
        phone_number = user.get('phone_number', '')
        if not phone_number or str(phone_number).startswith('web-'):
            flash('No phone number to verify', 'error')
            return redirect(url_for('dashboard_settings'))
        
        return render_template('dashboard/verify_phone.html', phone_number=phone_number)
    
    @app.route('/dashboard/logout')
    def dashboard_logout():
        """Logout"""
        auth_manager.logout()
        flash('Logged out successfully', 'success')
        return redirect(url_for('dashboard_login'))
    
    @app.route('/dashboard/forgot-password', methods=['GET', 'POST'])
    def dashboard_forgot_password():
        """Password reset request"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            
            if not email:
                return render_template('dashboard/forgot_password.html', error='Email required')
            
            success, error = auth_manager.request_password_reset(email)
            
            # Always show success message (don't reveal if email exists)
            flash('If that email exists, a password reset link has been sent.', 'info')
            return redirect(url_for('dashboard_login'))
        
        return render_template('dashboard/forgot_password.html')
    
    @app.route('/dashboard/reset-password', methods=['GET', 'POST'])
    def dashboard_reset_password():
        """Password reset with token"""
        token = request.args.get('token', '')
        
        if not token:
            flash('Invalid reset token', 'error')
            return redirect(url_for('dashboard_login'))
        
        if request.method == 'POST':
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            
            if not password:
                return render_template('dashboard/reset_password.html', token=token, error='Password required')
            
            if password != password_confirm:
                return render_template('dashboard/reset_password.html', token=token, error='Passwords do not match')
            
            if len(password) < 8:
                return render_template('dashboard/reset_password.html', token=token, error='Password must be at least 8 characters')
            
            success, error = auth_manager.reset_password(token, password)
            
            if success:
                flash('Password reset successfully! Please log in.', 'success')
                return redirect(url_for('dashboard_login'))
            else:
                return render_template('dashboard/reset_password.html', token=token, error=error or 'Password reset failed')
        
        return render_template('dashboard/reset_password.html', token=token)
    
    # ============================================================================
    # Dashboard Routes
    # ============================================================================
    
    @app.route('/dashboard')
    @app.route('/dashboard/')
    @require_login
    def dashboard_index():
        """Main dashboard"""
        return render_template('dashboard/index.html')
    
    @app.route('/dashboard/settings')
    @require_login
    def dashboard_settings():
        """Settings page"""
        user = auth_manager.get_current_user()
        return render_template('dashboard/settings.html', user=user)
    
    @app.route('/dashboard/chat')
    @require_login
    def dashboard_chat():
        """Chat test page"""
        return render_template('dashboard/chat.html')
    
    @app.route('/dashboard/api/chat', methods=['POST'])
    @require_login
    def dashboard_api_chat():
        """Process chat messages (same as SMS processing)"""
        user = auth_manager.get_current_user()
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        try:
            # Import MessageProcessor here to avoid circular imports
            from core.processor import MessageProcessor
            
            # Create message processor with the supabase client
            processor = MessageProcessor(supabase)
            
            # Get user's phone number
            # Web users have a placeholder phone_number like "web-{uuid}" from registration
            phone_number = user.get('phone_number')
            if not phone_number:
                # Fallback: use user_id as identifier (processor will create user if needed)
                phone_number = f"web-user-{user['id']}"
            
            # Process message
            response_text = processor.process_message(message, phone_number=phone_number)
            
            return jsonify({
                'success': True,
                'response': response_text or "I didn't understand that. Try sending 'help' for available commands."
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }), 500
    
    # ============================================================================
    # Dashboard API Routes (JSON endpoints)
    # ============================================================================
    
    @app.route('/api/dashboard/stats')
    @require_login
    def api_dashboard_stats():
        """Get dashboard stats for a specific date"""
        user = auth_manager.get_current_user()
        date_str = request.args.get('date', '')
        
        if not date_str:
            return jsonify({'error': 'Date required'}), 400
        
        stats = dashboard_data.get_date_stats(user['id'], date_str)
        return jsonify(stats)
    
    @app.route('/api/dashboard/trends')
    @require_login
    def api_dashboard_trends():
        """Get trends for a date range"""
        user = auth_manager.get_current_user()
        end_date = request.args.get('end_date', '')
        days = request.args.get('days', '7', type=int)
        
        if not end_date:
            return jsonify({'error': 'End date required'}), 400
        
        trends = dashboard_data.get_trends(user['id'], end_date, days)
        return jsonify(trends)
    
    @app.route('/api/dashboard/calendar')
    @require_login
    def api_dashboard_calendar():
        """Get calendar data for a month"""
        user = auth_manager.get_current_user()
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            return jsonify({'error': 'Year and month required'}), 400
        
        calendar_data = dashboard_data.get_calendar_data(user['id'], year, month)
        return jsonify(calendar_data)
    
    # Dashboard frontend expects these paths (used by index.html)
    @app.route('/dashboard/api/date/<date_str>')
    @require_login
    def dashboard_api_date(date_str):
        """Get date stats in frontend format"""
        user = auth_manager.get_current_user()
        data = dashboard_data.get_date_stats_for_frontend(user['id'], date_str)
        if data.get('error'):
            return jsonify(data), 500
        return jsonify(data)
    
    @app.route('/dashboard/api/trends/<int:days>')
    @require_login
    def dashboard_api_trends(days):
        """Get trends in frontend format"""
        user = auth_manager.get_current_user()
        end_date = request.args.get('end_date', '')
        if not end_date:
            from datetime import date
            end_date = date.today().isoformat()
        data = dashboard_data.get_trends_for_frontend(user['id'], end_date, days)
        if data.get('error'):
            return jsonify(data), 500
        return jsonify(data)
    
    # ============================================================================
    # Legacy Routes (for existing templates)
    # ============================================================================
    
    @app.route('/dashboard/optin')
    def dashboard_optin():
        """Opt-in page"""
        return render_template('dashboard/optin.html')
    
    @app.route('/dashboard/privacy')
    def dashboard_privacy():
        """Privacy policy page"""
        return render_template('dashboard/privacy.html')
    
    @app.route('/dashboard/terms')
    def dashboard_terms():
        """Terms and conditions page"""
        return render_template('dashboard/terms.html')
    
    # ============================================================================
    # Testing/Admin Routes (for Phase 8 background job testing)
    # ============================================================================
    
    @app.route('/dashboard/test')
    @require_login
    def dashboard_test():
        """Testing page for background jobs"""
        return render_template('dashboard/test.html')
    
    @app.route('/dashboard/api/test/jobs', methods=['GET'])
    @require_login
    def api_test_jobs():
        """Get status of all scheduled jobs"""
        if not job_scheduler:
            return jsonify({'error': 'Job scheduler not available'}), 500
        
        jobs = []
        for job in job_scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jsonify({
            'scheduler_running': job_scheduler.is_running(),
            'jobs': jobs
        })
    
    @app.route('/dashboard/api/test/trigger/<job_name>', methods=['POST'])
    @require_login
    def api_test_trigger_job(job_name):
        """Manually trigger a background job for testing"""
        try:
            if job_name == 'reminder_followups':
                if not reminder_service:
                    return jsonify({'error': 'Reminder service not available'}), 500
                reminder_service.check_reminder_followups()
                return jsonify({'success': True, 'message': 'Reminder follow-ups check triggered'})
            
            elif job_name == 'task_decay':
                if not reminder_service:
                    return jsonify({'error': 'Reminder service not available'}), 500
                reminder_service.check_task_decay()
                return jsonify({'success': True, 'message': 'Task decay check triggered'})
            
            elif job_name == 'gentle_nudges':
                if not notification_service:
                    return jsonify({'error': 'Notification service not available'}), 500
                notification_service.check_gentle_nudges()
                return jsonify({'success': True, 'message': 'Gentle nudges check triggered'})
            
            elif job_name == 'weekly_digest':
                if not notification_service:
                    return jsonify({'error': 'Notification service not available'}), 500
                notification_service.send_weekly_digest()
                return jsonify({'success': True, 'message': 'Weekly digest triggered'})
            
            elif job_name == 'integration_sync':
                if not sync_service:
                    return jsonify({'error': 'Sync service not available'}), 500
                sync_service.sync_all_integrations()
                return jsonify({'success': True, 'message': 'Integration sync triggered'})
            
            else:
                return jsonify({'error': f'Unknown job: {job_name}'}), 400
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
