"""
Web Routes
Flask routes for dashboard and authentication
"""

from functools import wraps
from typing import Callable

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

from core import can_use_feature, get_turn_quota, normalize_plan
from data import UserUsageRepository

from .auth import AuthManager
from .dashboard import DashboardData


def register_web_routes(app: Flask, supabase, auth_manager: AuthManager, dashboard_data: DashboardData,
                        job_scheduler=None, reminder_service=None, sync_service=None, notification_service=None,
                        limiter=None,
                        get_message_processor_fn=None,
                        get_agent_orchestrator_fn=None):
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

    def limit(rule: str):
        """Optional rate limiting wrapper (no-op if limiter not provided)."""
        if limiter is None:
            def _noop(fn: Callable) -> Callable:
                return fn
            return _noop
        return limiter.limit(rule)

    TRENDS_ALLOWED_METRICS = frozenset(['sleep', 'water', 'calories', 'protein', 'carbs', 'fat', 'todos', 'workouts', 'messages'])
    TRENDS_TF_DAYS = {'7d': 7, '14d': 14, '1m': 30, '1y': 365}

    # Stripe (optional - only needed if billing enabled)
    try:
        import stripe  # type: ignore
    except Exception:
        stripe = None

    # Message processor singleton (to preserve SMS-like conversation state in web chat)
    _processor = None

    def get_message_processor():
        nonlocal _processor
        if get_message_processor_fn is not None:
            return get_message_processor_fn()
        if _processor is None:
            from core.processor import MessageProcessor
            _processor = MessageProcessor(supabase)
        return _processor

    _agent = None

    def get_agent_orchestrator():
        nonlocal _agent
        if get_agent_orchestrator_fn is not None:
            return get_agent_orchestrator_fn()
        if _agent is None:
            from services.agent.orchestrator import AgentOrchestrator
            _agent = AgentOrchestrator(supabase)
        return _agent
    
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
        """Login endpoint (handles form submissions from modal)"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            success, user, error = auth_manager.login_with_email_password(email, password)
            
            if success:
                return jsonify({
                    'success': True,
                    'redirect': url_for('dashboard_index')
                }), 200
            else:
                return jsonify({'error': error or 'Login failed'}), 400
        
        # GET request - redirect to landing page (modals are there)
        return redirect(url_for('landing_page'))
    
    @app.route('/dashboard/register', methods=['GET', 'POST'])
    def dashboard_register():
        """Registration endpoint (handles form submissions from modal)"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            name = request.form.get('name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            timezone = request.form.get('timezone', '').strip()
            
            # Validation
            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            if not name:
                return jsonify({'error': 'Name is required'}), 400
            
            if not phone_number:
                return jsonify({'error': 'Phone number is required'}), 400

            # Normalize phone number to E.164 (US-only for now)
            # Accept: +1XXXXXXXXXX, 1XXXXXXXXXX, XXXXXXXXXX, or formatted like "+1 (123) 456-7890"
            import re
            digits = re.sub(r'\D', '', phone_number)
            if len(digits) == 10:
                phone_number = "+1" + digits
            elif len(digits) == 11 and digits.startswith("1"):
                phone_number = "+" + digits
            elif phone_number.startswith("+") and 1 < len(digits) <= 15:
                phone_number = "+" + digits
            else:
                return jsonify({'error': 'Phone number must be a valid US number (10 digits).'}), 400

            phone_regex = re.compile(r'^\+[1-9]\d{1,14}$')
            if not phone_regex.match(phone_number):
                return jsonify({'error': 'Phone number must be in E.164 format (e.g., +11234567890).'}), 400
            
            if password != password_confirm:
                return jsonify({'error': 'Passwords do not match'}), 400
            
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            # Register user with Supabase Auth
            success, user, error = auth_manager.register_with_email_password(
                email, password, name, phone_number, timezone=timezone or None
            )

            if success:
                if user and user.get('email_confirmation_required'):
                    return jsonify({
                        'success': True,
                        'email_confirmation_required': True,
                        'message': 'Check your email to confirm your account. Then you can log in.',
                    }), 200
                return jsonify({
                    'success': True,
                    'redirect': url_for('dashboard_index'),
                }), 200
            return jsonify({'error': error or 'Registration failed'}), 400
        
        # GET request - redirect to landing page (modals are there)
        return redirect(url_for('landing_page'))
    
    @app.route('/dashboard/logout')
    def dashboard_logout():
        """Logout"""
        auth_manager.logout()
        return redirect(url_for('dashboard_login'))
    
    @app.route('/dashboard/forgot-password', methods=['GET', 'POST'])
    def dashboard_forgot_password():
        """Password reset request (form POST or JSON for API)."""
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json(silent=True) or {}
                email = (data.get('email') or '').strip()
            else:
                email = request.form.get('email', '').strip()
            if not email:
                if request.is_json:
                    return jsonify({'success': False, 'error': 'Email required'}), 400
                return render_template('dashboard/forgot_password.html', error='Email required')
            auth_manager.request_password_reset(email)
            if request.is_json:
                return jsonify({'success': True, 'message': 'If that email exists, a reset link has been sent.'})
            flash('If that email exists, a password reset link has been sent.', 'info')
            return redirect(url_for('dashboard_login'))
        return render_template('dashboard/forgot_password.html')

    @app.route('/dashboard/reset-password', methods=['GET', 'POST'])
    def dashboard_reset_password():
        """
        Password reset page. Supabase redirects here from the email link with
        tokens in the URL hash (#access_token=...&type=recovery). The page uses
        Supabase JS to set session and call updateUser({ password }) on submit.
        Token in query string is optional (legacy); primary flow is client-side.
        """
        from config import Config
        token = request.args.get('token', '')
        supabase_url = (Config.SUPABASE_URL or '').rstrip('/')
        supabase_anon_key = Config.SUPABASE_KEY or ''
        if request.method == 'POST' and token:
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            if not password:
                return render_template(
                    'dashboard/reset_password.html',
                    token=token,
                    supabase_url=supabase_url,
                    supabase_anon_key=supabase_anon_key,
                    error='Password required',
                )
            if password != password_confirm:
                return render_template(
                    'dashboard/reset_password.html',
                    token=token,
                    supabase_url=supabase_url,
                    supabase_anon_key=supabase_anon_key,
                    error='Passwords do not match',
                )
            if len(password) < 8:
                return render_template(
                    'dashboard/reset_password.html',
                    token=token,
                    supabase_url=supabase_url,
                    supabase_anon_key=supabase_anon_key,
                    error='Password must be at least 8 characters',
                )
            success, error = auth_manager.reset_password(token, password)
            if success:
                flash('Password reset successfully! Please log in.', 'success')
                return redirect(url_for('dashboard_login'))
            return render_template(
                'dashboard/reset_password.html',
                token=token,
                supabase_url=supabase_url,
                supabase_anon_key=supabase_anon_key,
                error=error or 'Password reset failed',
            )
        return render_template(
            'dashboard/reset_password.html',
            token=token,
            supabase_url=supabase_url,
            supabase_anon_key=supabase_anon_key,
        )
    
    # ============================================================================
    # Dashboard Routes
    # ============================================================================
    
    @app.route('/dashboard')
    @app.route('/dashboard/')
    @require_login
    def dashboard_index():
        """Main dashboard"""
        user = auth_manager.get_current_user()
        return render_template('dashboard/index.html', user=user, active_page='dashboard')
    
    @app.route('/dashboard/settings')
    @require_login
    def dashboard_settings():
        """Settings page"""
        user = auth_manager.get_current_user()
        return render_template('dashboard/settings.html', user=user, active_page='settings')

    @app.route('/dashboard/preferences')
    @require_login
    def dashboard_preferences():
        """Preferences page"""
        user = auth_manager.get_current_user()
        try:
            from data import UserPreferencesRepository
            prefs_repo = UserPreferencesRepository(supabase)
            prefs = prefs_repo.ensure(user['id']) if user else {}
        except Exception:
            prefs = {}
        return render_template('dashboard/preferences.html', user=user, prefs=prefs, active_page='preferences')

    @app.route('/dashboard/trends')
    @require_login
    def dashboard_trends():
        """Trends page (Core/Pro)."""
        user = auth_manager.get_current_user()
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "trends"):
            flash("Trends are available on Core and Pro plans. Upgrade to view.", "info")
            return redirect(url_for("dashboard_pricing"))
        return render_template("dashboard/trends.html", user=user, active_page="trends")

    @app.route('/dashboard/pricing')
    @require_login
    def dashboard_pricing():
        """Pricing page (placeholder plans; details TBD)."""
        user = auth_manager.get_current_user()
        return render_template('dashboard/pricing.html', user=user, active_page='pricing')

    # ============================================================================
    # Billing (Stripe Checkout) - Core/Pro subscriptions
    # ============================================================================

    def _stripe_price_id_for(plan: str, interval: str) -> str:
        from config import Config
        plan = (plan or "").strip().lower()
        interval = (interval or "").strip().lower()
        if plan == "core" and interval == "monthly":
            return Config.STRIPE_PRICE_CORE_MONTHLY
        if plan == "core" and interval == "annual":
            return Config.STRIPE_PRICE_CORE_ANNUAL
        if plan == "pro" and interval == "monthly":
            return Config.STRIPE_PRICE_PRO_MONTHLY
        if plan == "pro" and interval == "annual":
            return Config.STRIPE_PRICE_PRO_ANNUAL
        return ""

    def _plan_from_price_id(price_id: str) -> dict:
        """Map a Stripe price id -> {plan, interval}."""
        from config import Config
        if not price_id:
            return {"plan": "free", "interval": None}
        if price_id == Config.STRIPE_PRICE_CORE_MONTHLY:
            return {"plan": "core", "interval": "monthly"}
        if price_id == Config.STRIPE_PRICE_CORE_ANNUAL:
            return {"plan": "core", "interval": "annual"}
        if price_id == Config.STRIPE_PRICE_PRO_MONTHLY:
            return {"plan": "pro", "interval": "monthly"}
        if price_id == Config.STRIPE_PRICE_PRO_ANNUAL:
            return {"plan": "pro", "interval": "annual"}
        return {"plan": "free", "interval": None}

    @app.route('/dashboard/api/billing/checkout', methods=['POST'])
    @require_login
    def dashboard_api_billing_checkout():
        """Create a Stripe Checkout session for Core/Pro. Free never requires card."""
        from config import Config
        if stripe is None:
            return jsonify({"success": False, "error": "Stripe dependency not installed"}), 500
        if not Config.STRIPE_SECRET_KEY:
            return jsonify({"success": False, "error": "Stripe is not configured (missing STRIPE_SECRET_KEY)"}), 500

        user = auth_manager.get_current_user()
        payload = request.get_json(silent=True) or {}
        plan = (payload.get("plan") or "").strip().lower()
        interval = (payload.get("interval") or "").strip().lower()

        if plan not in ("core", "pro"):
            return jsonify({"success": False, "error": "Invalid plan"}), 400
        if interval not in ("monthly", "annual"):
            return jsonify({"success": False, "error": "Invalid interval"}), 400

        price_id = _stripe_price_id_for(plan, interval)
        if not price_id:
            return jsonify({"success": False, "error": "Price ID not configured for this plan/interval"}), 500

        stripe.api_key = Config.STRIPE_SECRET_KEY

        # Ensure Stripe customer exists
        stripe_customer_id = user.get("stripe_customer_id")
        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.get("email") or None,
                name=user.get("name") or None,
                phone=user.get("phone_number") or None,
                metadata={"user_id": str(user.get("id"))},
            )
            stripe_customer_id = customer.get("id")
            try:
                supabase.table("users").update({"stripe_customer_id": stripe_customer_id}).eq("id", int(user["id"])).execute()
            except Exception:
                pass

        base_url = (Config.BASE_URL or "").rstrip("/")
        if not base_url:
            base_url = request.host_url.rstrip("/")

        session_obj = stripe.checkout.Session.create(
            mode="subscription",
            customer=stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=False,
            client_reference_id=str(user.get("id")),
            subscription_data={
                "metadata": {
                    "user_id": str(user.get("id")),
                    "plan": plan,
                    "interval": interval,
                }
            },
            success_url=f"{base_url}/dashboard/pricing?success=1",
            cancel_url=f"{base_url}/dashboard/pricing?canceled=1",
        )

        return jsonify({"success": True, "url": session_obj.get("url")})

    @app.route('/dashboard/api/billing/portal', methods=['POST'])
    @require_login
    def dashboard_api_billing_portal():
        """Open Stripe Billing Portal (optional)."""
        from config import Config
        if stripe is None:
            return jsonify({"success": False, "error": "Stripe dependency not installed"}), 500
        if not Config.STRIPE_SECRET_KEY:
            return jsonify({"success": False, "error": "Stripe is not configured"}), 500
        stripe.api_key = Config.STRIPE_SECRET_KEY

        user = auth_manager.get_current_user()
        stripe_customer_id = user.get("stripe_customer_id")
        if not stripe_customer_id:
            return jsonify({"success": False, "error": "No Stripe customer found for this user"}), 400

        base_url = (Config.BASE_URL or "").rstrip("/")
        if not base_url:
            base_url = request.host_url.rstrip("/")

        portal = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{base_url}/dashboard/settings",
        )
        return jsonify({"success": True, "url": portal.get("url")})

    @app.route('/stripe/webhook', methods=['POST'])
    def stripe_webhook():
        """Stripe webhook (source of truth for subscription state)."""
        from config import Config
        if stripe is None:
            return jsonify({"success": False, "error": "Stripe dependency not installed"}), 500
        if not Config.STRIPE_WEBHOOK_SECRET or not Config.STRIPE_SECRET_KEY:
            return jsonify({"success": False, "error": "Stripe webhook not configured"}), 500

        stripe.api_key = Config.STRIPE_SECRET_KEY

        payload = request.get_data(cache=False, as_text=False)
        sig_header = request.headers.get("Stripe-Signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, Config.STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid signature: {str(e)}"}), 400

        etype = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}

        def _update_user_by_customer(customer_id: str, updates: dict):
            if not customer_id:
                return
            try:
                supabase.table("users").update(updates).eq("stripe_customer_id", customer_id).execute()
            except Exception:
                pass

        def _update_user_by_id(user_id: int, updates: dict):
            try:
                supabase.table("users").update(updates).eq("id", int(user_id)).execute()
            except Exception:
                pass

        def _iso_from_unix(ts: int):
            try:
                from datetime import datetime, timezone
                return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
            except Exception:
                return None

        if etype == "checkout.session.completed":
            if obj.get("mode") == "subscription":
                customer_id = obj.get("customer")
                sub_id = obj.get("subscription")
                user_id = obj.get("client_reference_id")
                if user_id:
                    _update_user_by_id(int(user_id), {
                        "stripe_customer_id": customer_id,
                        "stripe_subscription_id": sub_id,
                    })
            return jsonify({"received": True})

        if etype in ("customer.subscription.created", "customer.subscription.updated"):
            customer_id = obj.get("customer")
            sub_id = obj.get("id")
            status = obj.get("status")
            cancel_at_period_end = bool(obj.get("cancel_at_period_end") or False)
            current_period_end = _iso_from_unix(obj.get("current_period_end")) if obj.get("current_period_end") else None

            price_id = None
            try:
                items = (obj.get("items") or {}).get("data") or []
                if items and items[0].get("price"):
                    price_id = items[0]["price"].get("id")
            except Exception:
                price_id = None

            mapped = _plan_from_price_id(price_id or "")
            plan = mapped.get("plan") or "free"
            interval = mapped.get("interval")

            updates = {
                "stripe_subscription_id": sub_id,
                "stripe_subscription_status": status,
                "stripe_price_id": price_id,
                "stripe_current_period_end": current_period_end,
                "stripe_cancel_at_period_end": cancel_at_period_end,
                "plan": plan,
                "plan_interval": interval,
            }
            _update_user_by_customer(customer_id, updates)
            return jsonify({"received": True})

        if etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            sub_id = obj.get("id")
            updates = {
                "stripe_subscription_id": sub_id,
                "stripe_subscription_status": "canceled",
                "stripe_price_id": None,
                "stripe_current_period_end": None,
                "stripe_cancel_at_period_end": False,
                "plan": "free",
                "plan_interval": None,
            }
            _update_user_by_customer(customer_id, updates)
            return jsonify({"received": True})

        # Ignore other events for now
        return jsonify({"received": True})

    @app.route('/dashboard/api/settings/profile', methods=['POST'])
    @require_login
    def dashboard_api_settings_profile():
        """Update user profile fields (timezone, location, etc.)"""
        user = auth_manager.get_current_user()
        data = request.get_json(silent=True) or {}
        if not user:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        updates = {}
        for key in ['name', 'timezone', 'location_name', 'location_lat', 'location_lon', 'morning_checkin_hour']:
            if key in data and data[key] is not None:
                updates[key] = data[key]

        # Basic coercions
        if 'morning_checkin_hour' in updates:
            try:
                updates['morning_checkin_hour'] = int(updates['morning_checkin_hour'])
            except Exception:
                return jsonify({'success': False, 'error': 'morning_checkin_hour must be 0-23'}), 400

        if 'location_lat' in updates:
            try:
                updates['location_lat'] = float(updates['location_lat'])
            except Exception:
                updates.pop('location_lat', None)
        if 'location_lon' in updates:
            try:
                updates['location_lon'] = float(updates['location_lon'])
            except Exception:
                updates.pop('location_lon', None)

        try:
            from data import UserRepository
            repo = UserRepository(supabase)
            repo.update(user['id'], updates)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/dashboard/api/settings/preferences', methods=['POST'])
    @require_login
    def dashboard_api_settings_preferences():
        """Update user preference fields (quiet hours, units, goals, toggles, digest schedule)."""
        user = auth_manager.get_current_user()
        data = request.get_json(silent=True) or {}
        if not user:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        allowed = {
            'units',
            'quiet_hours_start', 'quiet_hours_end', 'do_not_disturb',
            'weekly_digest_day', 'weekly_digest_hour',
            'default_water_goal_ml',
            'default_calories_goal', 'default_protein_goal', 'default_carbs_goal', 'default_fat_goal',
            'morning_include_reminders', 'morning_include_weather', 'morning_include_quote',
        }
        updates = {k: v for k, v in data.items() if k in allowed}

        # Basic coercions
        for k in ['quiet_hours_start', 'quiet_hours_end', 'weekly_digest_day', 'weekly_digest_hour']:
            if k in updates and updates[k] is not None:
                try:
                    updates[k] = int(updates[k])
                except Exception:
                    return jsonify({'success': False, 'error': f'{k} must be an integer'}), 400

        for k in ['default_water_goal_ml', 'default_calories_goal', 'default_protein_goal', 'default_carbs_goal', 'default_fat_goal']:
            if k in updates and updates[k] not in (None, ''):
                try:
                    updates[k] = int(float(updates[k]))
                except Exception:
                    return jsonify({'success': False, 'error': f'{k} must be a number'}), 400
            elif k in updates and updates[k] in (None, ''):
                updates[k] = None

        for k in ['do_not_disturb', 'morning_include_reminders', 'morning_include_weather', 'morning_include_quote']:
            if k in updates:
                updates[k] = bool(updates[k])

        if 'units' in updates and updates['units'] not in ('metric', 'imperial'):
            return jsonify({'success': False, 'error': 'units must be metric or imperial'}), 400

        try:
            from data import UserPreferencesRepository
            repo = UserPreferencesRepository(supabase)
            repo.ensure(user['id'])
            repo.update(user['id'], updates)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/dashboard/chat')
    @require_login
    def dashboard_chat():
        """Chat test page"""
        user = auth_manager.get_current_user()
        return render_template('dashboard/chat.html', user=user, active_page='chat')

    def _vision_extract_to_log_food_items(extracted: dict) -> list:
        """Convert vision analyze_food_image output to log_food items list."""
        etype = (extracted.get("type") or "unknown").lower()
        items = []
        if etype == "label":
            per = extracted.get("per_serving") or {}
            servings = extracted.get("servings_consumed")
            try:
                servings = float(servings) if servings is not None else 1.0
            except Exception:
                servings = 1.0
            items.append({
                "food_name": (extracted.get("product_name") or "food from label").strip(),
                "calories": float(per.get("calories") or 0),
                "protein": float(per.get("protein_g") or 0),
                "carbs": float(per.get("carbs_g") or 0),
                "fat": float(per.get("fat_g") or 0),
                "restaurant": None,
                "portion_multiplier": float(servings or 1.0),
            })
        elif etype == "receipt":
            for it in (extracted.get("items") or []):
                name = (it.get("name") or "item").strip()
                qty = 1
                try:
                    q = it.get("quantity")
                    if q is not None:
                        qty = max(1, int(float(q)))
                except Exception:
                    pass
                items.append({
                    "food_name": name,
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0,
                    "restaurant": extracted.get("merchant"),
                    "portion_multiplier": float(qty),
                })
        return items

    @app.route('/dashboard/api/chat', methods=['POST'])
    @limit("30 per minute")
    @require_login
    def dashboard_api_chat():
        """Process chat messages (same as SMS). Optional image: image_upload_id or image_base64."""
        user = auth_manager.get_current_user()
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        image_upload_id = data.get('image_upload_id')
        image_base64 = data.get('image_base64')

        if not message and not image_upload_id and not image_base64:
            return jsonify({'success': False, 'error': 'Message or image required'}), 400

        if message and len(message) > 300:
            return jsonify({'success': False, 'error': 'Message must be 300 characters or less'}), 400

        try:
            from config import Config
            phone_number = user.get('phone_number') or f"web-user-{user['id']}"
            response_text = None
            quota_exceeded = False

            # Check quota first; when over limit we do not process message or image—only send limit message + pricing link.
            if user.get("onboarding_complete", False):
                try:
                    plan = normalize_plan(user.get("plan"))
                    quota = get_turn_quota(plan)
                    if quota is not None:
                        month_key = UserUsageRepository.month_key_for()
                        row = UserUsageRepository(supabase).get_month(
                            int(user["id"]), month_key
                        )
                        used = int((row.get("turns_used") if row else 0) or 0)
                        if used >= quota:
                            base_url = (Config.BASE_URL or request.host_url or "").rstrip("/")
                            pricing_url = f"{base_url}/dashboard/pricing" if base_url else "/dashboard/pricing"
                            response_text = [
                                "You've hit your monthly message limit for this plan.",
                                "Upgrade to Pro for unlimited messaging (with fair-use safeguards).",
                                pricing_url,
                            ]
                            quota_exceeded = True
                except Exception:
                    pass

            if not quota_exceeded:
                pre_run_tool_results = None
                effective_message = message or "I just sent a photo of my food."
                if (image_upload_id or image_base64) and user.get("onboarding_complete", False):
                    image_url = None
                    if image_upload_id:
                        try:
                            from data import FoodImageUploadRepository
                            upload_repo = FoodImageUploadRepository(supabase)
                            row = upload_repo.get_by_id(int(image_upload_id))
                            if row and int(row.get("user_id") or -1) == int(user["id"]):
                                bucket, path = row.get("bucket"), row.get("path")
                                if bucket and path:
                                    signed = supabase.storage.from_(bucket).create_signed_url(path, 600)
                                    image_url = (signed.get("signedUrl") or signed.get("signed_url") if isinstance(signed, dict) else getattr(signed, "signedUrl", None) or getattr(signed, "signed_url", None))
                        except Exception:
                            pass
                    elif image_base64:
                        raw = (image_base64 or "").strip()
                        image_url = raw if raw.startswith("data:") else (f"data:image/jpeg;base64,{raw}" if raw else None)
                    if image_url:
                        try:
                            from services.vision import OpenAIVisionClient
                            vision = OpenAIVisionClient()
                            extracted = vision.analyze_food_image(image_url=image_url, kind_hint="unknown")
                            log_items = _vision_extract_to_log_food_items(extracted)
                            if log_items:
                                agent = get_agent_orchestrator()
                                tr = agent.tools.execute(
                                    user_id=int(user["id"]),
                                    tool_name="log_food",
                                    arguments={"items": log_items, "source": "photo", "metadata": {"from_chat_image": True}},
                                )
                                if tr.ok:
                                    pre_run_tool_results = {"log_food": {"ok": True, "result": tr.result, "error": tr.error}}
                                    effective_message = "I just sent a photo of my food; please confirm it's logged."
                        except Exception:
                            pass

            if not quota_exceeded:
                response_text = None
            try:
                if not quota_exceeded and user.get("onboarding_complete", False):
                    quota_blocked = False
                    try:
                        plan = normalize_plan(user.get("plan"))
                        quota = get_turn_quota(plan)
                        if quota is not None:
                            month_key = UserUsageRepository.month_key_for()
                            row = UserUsageRepository(supabase).get_month(
                                int(user["id"]), month_key
                            )
                            used = int((row.get("turns_used") if row else 0) or 0)
                            if used >= quota:
                                response_text = [
                                    "You’ve hit your monthly message limit for this plan.",
                                    "Upgrade to Pro for unlimited messaging (with fair-use safeguards).",
                                ]
                                quota_blocked = True
                    except Exception:
                        pass

                    if not quota_blocked:
                        agent = get_agent_orchestrator()
                        response_text = agent.handle_message(
                            user_id=int(user["id"]),
                            phone_number=str(phone_number),
                            text=effective_message,
                            source="web",
                            pre_run_tool_results=pre_run_tool_results,
                        )
                        try:
                            UserUsageRepository(supabase).increment_month(
                                int(user["id"]),
                                UserUsageRepository.month_key_for(),
                                delta=1,
                            )
                        except Exception:
                            pass
            except Exception:
                if not quota_exceeded:
                    response_text = None

            if response_text is None:
                effective_message = message or "I just sent a photo of my food."
                processor = get_message_processor()
                response_text = processor.process_message(effective_message, phone_number=phone_number)

            # Optional in-thread nudge (e.g. "Want to log water?")
            include_nudge = data.get("include_nudge") is True
            if include_nudge and response_text and user.get("onboarding_complete", False) and not quota_exceeded:
                nudge = "Want to log water or track a workout?"
                if isinstance(response_text, (list, tuple)):
                    response_text = list(response_text) + [nudge]
                else:
                    response_text = [response_text, nudge]

            # Mirror Twilio response behavior (truncate for SMS-like output)
            if isinstance(response_text, (list, tuple)):
                parts = []
                for part in response_text:
                    if not part:
                        continue
                    if len(part) > 1500:
                        part = part[:1500] + "..."
                    parts.append(part)
                payload = {
                    "success": True,
                    "responses": parts,
                    "response": ("\n\n".join(parts) if parts else "I didn't understand that. Try sending 'help' for available commands."),
                }
                if quota_exceeded:
                    base_url = (Config.BASE_URL or request.host_url or "").rstrip("/")
                    payload["quota_exceeded"] = True
                    payload["pricing_url"] = f"{base_url}/dashboard/pricing" if base_url else "/dashboard/pricing"
                return jsonify(payload)

            if response_text and len(response_text) > 1500:
                response_text = response_text[:1500] + "..."

            return jsonify({
                'success': True,
                'response': response_text or "I didn't understand that. Try sending 'help' for available commands."
            })
        except Exception as e:
            # In SMS, users never see stack traces—keep parity by returning a generic response.
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': True,
                'response': "Sorry, I encountered an error processing your message. Please try again."
            }), 200

    # ============================================================================
    # Dashboard Uploads (Food images)
    # ============================================================================

    @app.route('/dashboard/api/upload/image', methods=['POST'])
    @limit("10 per minute")
    @require_login
    def dashboard_api_upload_image():
        """
        Upload an image (nutrition label / receipt / food photo) to Supabase Storage and
        store metadata in the database.

        Expects multipart form-data:
        - image: file
        - kind: optional string ('label'|'receipt'|'plated'|'unknown')
        """
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "image_upload"):
            return jsonify({"success": False, "error": "Image upload requires Core or Pro."}), 403

        file = request.files.get('image')
        if not file:
            return jsonify({'success': False, 'error': 'Missing image file (form field: image)'}), 400

        kind = (request.form.get('kind', '') or '').strip().lower() or None
        if kind not in (None, 'label', 'receipt', 'plated', 'unknown'):
            return jsonify({'success': False, 'error': 'kind must be one of: label, receipt, plated, unknown'}), 400

        # Read bytes (enforce max size)
        from config import Config
        max_bytes = int(getattr(Config, 'FOOD_IMAGE_MAX_BYTES', 6_000_000) or 6_000_000)
        data = file.read()
        size_bytes = len(data or b'')
        if size_bytes <= 0:
            return jsonify({'success': False, 'error': 'Empty file'}), 400
        if size_bytes > max_bytes:
            return jsonify({'success': False, 'error': f'File too large (max {max_bytes} bytes)'}), 413

        # Basic content-type allowlist
        mime_type = (file.mimetype or '').lower()
        allowed = {'image/jpeg', 'image/png', 'image/webp'}
        if mime_type not in allowed:
            return jsonify({'success': False, 'error': f'Unsupported image type: {mime_type}'}), 400

        # Build storage path
        import uuid
        import os
        ext = os.path.splitext(file.filename or '')[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            # Fall back based on mime
            ext = '.jpg' if mime_type == 'image/jpeg' else ('.png' if mime_type == 'image/png' else '.webp')

        bucket = getattr(Config, 'FOOD_IMAGE_BUCKET', 'food-uploads') or 'food-uploads'
        key = str(uuid.uuid4())
        path = f"user_{user['id']}/{key}{ext}"

        # Upload to Supabase Storage
        try:
            # supabase-py: storage.from_(bucket).upload(path, data, {contentType, upsert})
            supabase.storage.from_(bucket).upload(
                path,
                data,
                {
                    'contentType': mime_type,
                    'upsert': False,
                },
            )
        except Exception as e:
            return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'}), 500

        # Store metadata
        try:
            from data import FoodImageUploadRepository
            repo = FoodImageUploadRepository(supabase)
            row = repo.create_upload(
                user_id=int(user['id']),
                bucket=bucket,
                path=path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                status='uploaded',
                kind=kind or 'unknown',
                original_filename=(file.filename or None),
            )
            if not row:
                return jsonify({'success': False, 'error': 'Upload saved but metadata insert failed'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': f'Upload saved but metadata insert failed: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'upload_id': row.get('id'),
            'bucket': bucket,
            'path': path,
            'kind': row.get('kind'),
            'size_bytes': size_bytes,
            'mime_type': mime_type,
        })

    @app.route('/dashboard/api/food/image/process', methods=['POST'])
    @limit("5 per minute")
    @require_login
    def dashboard_api_process_food_image():
        """
        Process a previously uploaded food image:
        - create a signed URL from Supabase Storage
        - run OpenAI vision to extract either a nutrition label or receipt items
        - insert food_logs entries
        - store extraction results back on food_image_uploads

        JSON body:
        - upload_id: integer
        """
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        payload = request.get_json(silent=True) or {}
        upload_id = payload.get("upload_id")
        try:
            upload_id_int = int(upload_id)
        except Exception:
            return jsonify({'success': False, 'error': 'upload_id must be an integer'}), 400

        from data import FoodImageUploadRepository, FoodRepository, FoodLogMetadataRepository
        upload_repo = FoodImageUploadRepository(supabase)
        food_repo = FoodRepository(supabase)
        meta_repo = FoodLogMetadataRepository(supabase)

        # Fetch upload row and verify ownership
        try:
            row = upload_repo.get_by_id(upload_id_int)
        except Exception:
            row = None
        if not row:
            return jsonify({'success': False, 'error': 'Upload not found'}), 404
        if int(row.get("user_id") or -1) != int(user["id"]):
            return jsonify({'success': False, 'error': 'Forbidden'}), 403

        bucket = row.get("bucket")
        path = row.get("path")
        kind = row.get("kind") or "unknown"
        if not bucket or not path:
            return jsonify({'success': False, 'error': 'Upload record missing bucket/path'}), 500

        # Create signed URL for the image (private bucket friendly)
        try:
            signed = supabase.storage.from_(bucket).create_signed_url(path, 600)
            signed_url = None
            # supabase-py may return dict-like or object-like
            if isinstance(signed, dict):
                signed_url = signed.get("signedUrl") or signed.get("signed_url")
            else:
                signed_url = getattr(signed, "signedUrl", None) or getattr(signed, "signed_url", None)
            if not signed_url:
                return jsonify({'success': False, 'error': 'Failed to generate signed URL'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to generate signed URL: {str(e)}'}), 500

        # Run vision extraction
        try:
            from services.vision import OpenAIVisionClient
            vision = OpenAIVisionClient()
            extracted = vision.analyze_food_image(image_url=signed_url, kind_hint=kind)
        except Exception as e:
            # mark as failed
            try:
                upload_repo.update(upload_id_int, {"status": "failed", "error": str(e)})
            except Exception:
                pass
            return jsonify({'success': False, 'error': f'Vision analysis failed: {str(e)}'}), 500

        created_logs = []
        created_meta = []
        unresolved_items = []

        try:
            etype = (extracted.get("type") or "unknown").lower()
            confidence = float(extracted.get("confidence") or 0.5)

            if etype == "label":
                product_name = extracted.get("product_name") or "nutrition label"
                per = extracted.get("per_serving") or {}
                servings = extracted.get("servings_consumed")
                try:
                    servings = float(servings) if servings is not None else 1.0
                except Exception:
                    servings = 1.0

                created = food_repo.create_food_log(
                    user_id=int(user["id"]),
                    food_name=str(product_name),
                    calories=float(per.get("calories") or 0),
                    protein=float(per.get("protein_g") or 0),
                    carbs=float(per.get("carbs_g") or 0),
                    fat=float(per.get("fat_g") or 0),
                    restaurant=None,
                    portion_multiplier=float(servings or 1.0),
                )
                created_logs.append(created)

                meta = meta_repo.create_metadata(
                    food_log_id=int(created.get("id")),
                    source="label_ocr",
                    confidence=confidence,
                    basis="serving",
                    serving_weight_grams=extracted.get("serving_weight_grams"),
                    resolved_name=product_name,
                    raw_query=None,
                    raw=extracted,
                )
                if meta:
                    created_meta.append(meta)

            elif etype == "receipt":
                merchant = extracted.get("merchant")
                items = extracted.get("items") or []

                # Resolve each item via nutrition resolver
                from services.nutrition import NutritionResolver
                resolver = NutritionResolver(supabase)

                for it in items[:25]:
                    name = (it.get("name") or "").strip()
                    if not name:
                        continue
                    qty = it.get("quantity")
                    try:
                        qty_f = float(qty) if qty is not None else 1.0
                    except Exception:
                        qty_f = 1.0
                    if qty_f <= 0:
                        qty_f = 1.0

                    nut = resolver.resolve(query=name, restaurant=merchant)
                    if not nut or (
                        (nut.calories is None)
                        and (nut.protein_g is None)
                        and (nut.carbs_g is None)
                        and (nut.fat_g is None)
                    ):
                        unresolved_items.append({"name": name, "quantity": qty_f})
                        continue

                    calories = float(nut.calories or 0)
                    protein = float(nut.protein_g or 0)
                    carbs = float(nut.carbs_g or 0)
                    fat = float(nut.fat_g or 0)
                    source = nut.source
                    conf = float(nut.confidence)

                    created = food_repo.create_food_log(
                        user_id=int(user["id"]),
                        food_name=name,
                        calories=calories,
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                        restaurant=merchant,
                        portion_multiplier=qty_f,
                    )
                    created_logs.append(created)

                    meta = meta_repo.create_metadata(
                        food_log_id=int(created.get("id")),
                        source=source,
                        confidence=conf,
                        basis=(nut.basis if nut else None),
                        serving_weight_grams=(nut.serving_weight_grams if nut else None),
                        resolved_name=(nut.resolved_name if nut else None),
                        raw_query=name,
                        raw={"upload_extraction": extracted, "resolved": (nut.raw if nut else None)},
                    )
                    if meta:
                        created_meta.append(meta)

            # Update upload record
            upload_repo.update(upload_id_int, {"status": "processed", "extracted": extracted, "error": None})
        except Exception as e:
            try:
                upload_repo.update(upload_id_int, {"status": "failed", "extracted": extracted, "error": str(e)})
            except Exception:
                pass
            return jsonify({'success': False, 'error': f'Failed to create food logs: {str(e)}', 'extracted': extracted}), 500

        return jsonify({
            "success": True,
            "upload_id": upload_id_int,
            "extracted": extracted,
            "created_logs": [{"id": r.get("id"), "food_name": r.get("food_name")} for r in created_logs],
            "unresolved_items": unresolved_items,
        })

    @app.route('/dashboard/api/upload/image/delete', methods=['POST'])
    @limit("10 per minute")
    @require_login
    def dashboard_api_delete_uploaded_image():
        """
        Delete an uploaded image and its metadata (privacy cleanup). Core/Pro.
        JSON body:
        - upload_id: integer
        """
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "image_upload"):
            return jsonify({"success": False, "error": "Image upload requires Core or Pro."}), 403

        payload = request.get_json(silent=True) or {}
        upload_id = payload.get("upload_id")
        try:
            upload_id_int = int(upload_id)
        except Exception:
            return jsonify({'success': False, 'error': 'upload_id must be an integer'}), 400

        from data import FoodImageUploadRepository
        repo = FoodImageUploadRepository(supabase)
        row = repo.get_by_id(upload_id_int)
        if not row:
            return jsonify({'success': False, 'error': 'Upload not found'}), 404
        if int(row.get("user_id") or -1) != int(user["id"]):
            return jsonify({'success': False, 'error': 'Forbidden'}), 403

        bucket = row.get("bucket")
        path = row.get("path")
        try:
            if bucket and path:
                supabase.storage.from_(bucket).remove([path])
        except Exception:
            # continue even if storage deletion fails (user can retry)
            pass

        try:
            supabase.table("food_image_uploads").delete().eq("id", upload_id_int).execute()
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to delete metadata: {str(e)}'}), 500

        return jsonify({'success': True, 'deleted': True})
    
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
        """Get trends for a date range (Core/Pro)."""
        user = auth_manager.get_current_user()
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "trends"):
            return jsonify({"success": False, "error": "Trends require Core or Pro."}), 403
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
        """Get trends in frontend format (Core/Pro)."""
        user = auth_manager.get_current_user()
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "trends"):
            return jsonify({"success": False, "error": "Trends require Core or Pro."}), 403
        end_date = request.args.get('end_date', '')
        if not end_date:
            from datetime import date
            end_date = date.today().isoformat()
        data = dashboard_data.get_trends_for_frontend(user['id'], end_date, days)
        if data.get('error'):
            return jsonify(data), 500
        return jsonify(data)

    @app.route('/dashboard/api/trends/activity')
    @require_login
    def dashboard_api_trends_activity():
        """
        Activity log for Trends page (Core/Pro).
        Query params:
        - timeframe: '7d' | '14d' | '1m' | '1y' (preferred)
        - days: int (fallback)
        """
        from datetime import date, timedelta, datetime

        user = auth_manager.get_current_user()
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "trends"):
            return jsonify({"success": False, "error": "Trends require Core or Pro."}), 403
        uid = int(user['id'])
        tf = (request.args.get('timeframe') or '').strip()
        metric = (request.args.get('metric') or '').strip()
        days_q = request.args.get('days')

        days = TRENDS_TF_DAYS.get(tf)
        if days is None and days_q:
            try:
                days = max(1, min(365, int(days_q)))
            except Exception:
                days = 7
        if days is None:
            days = 7

        end_d = date.today()
        start_d = end_d - timedelta(days=days - 1)
        start_date = start_d.isoformat()
        end_date = end_d.isoformat()

        def _safe_iso(dt_str: str) -> str:
            if not dt_str:
                return ''
            return str(dt_str).replace(' ', 'T')

        def _dt_key(dt_str: str):
            if not dt_str:
                return datetime.min
            s = str(dt_str)
            if len(s) == 10:  # YYYY-MM-DD
                s = s + "T00:00:00"
            s = s.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return datetime.min

        items = []
        metric = metric if metric in TRENDS_ALLOWED_METRICS else ''

        _metric_types = {'calories': {'food'}, 'protein': {'food'}, 'carbs': {'food'}, 'fat': {'food'}, 'water': {'water'}, 'sleep': {'sleep'}, 'workouts': {'workout'}, 'todos': {'todo', 'reminder'}, 'messages': {'message'}}

        def _metric_allows(t: str) -> bool:
            return not metric or t in _metric_types.get(metric, set())

        try:
            food_logs = dashboard_data.food_repo.get_by_date_range(uid, start_date, end_date)
            for log in (food_logs or []):
                ts = _safe_iso(log.get('timestamp'))
                kcal = log.get('calories')
                pm = float(log.get('portion_multiplier') or 1.0)
                title = (log.get('food_name') or 'Food').strip()
                subtitle_parts = []
                if kcal is not None:
                    try:
                        subtitle_parts.append(f"{int(float(kcal) * pm)} cal")
                    except Exception:
                        subtitle_parts.append(f"{kcal} cal")
                rest = log.get('restaurant')
                if rest:
                    subtitle_parts.append(str(rest))
                items.append({
                    "type": "food",
                    "timestamp": ts,
                    "title": title,
                    "subtitle": " • ".join(subtitle_parts) if subtitle_parts else "Food log",
                })
        except Exception:
            pass

        try:
            water_logs = dashboard_data.water_repo.get_by_date_range(uid, start_date, end_date)
            for log in (water_logs or []):
                ts = _safe_iso(log.get('timestamp'))
                amt = log.get('amount_ml')
                subtitle = f"{amt} ml" if amt is not None else "Water log"
                items.append({
                    "type": "water",
                    "timestamp": ts,
                    "title": "Water",
                    "subtitle": subtitle,
                })
        except Exception:
            pass

        try:
            gym_logs = dashboard_data.gym_repo.get_by_date_range(uid, start_date, end_date)
            for log in (gym_logs or []):
                ts = _safe_iso(log.get('timestamp'))
                ex = (log.get('exercise') or 'Workout').strip()
                sets = log.get('sets')
                reps = log.get('reps')
                weight = log.get('weight')
                parts = []
                if sets and reps:
                    parts.append(f"{sets}×{reps}")
                elif sets:
                    parts.append(f"{sets} sets")
                if weight is not None and weight != '':
                    parts.append(f"@ {weight}")
                items.append({
                    "type": "workout",
                    "timestamp": ts,
                    "title": ex,
                    "subtitle": " • ".join(parts) if parts else "Workout log",
                })
        except Exception:
            pass

        try:
            sleep_logs = dashboard_data.sleep_repo.get_by_date_range(uid, start_date, end_date)
            for log in (sleep_logs or []):
                d = log.get('date') or ''
                wake = log.get('wake_time') or '00:00:00'
                ts = _safe_iso(f"{d}T{wake}") if d else ''
                dur = log.get('duration_hours')
                subtitle = f"{dur} hours" if dur is not None else "Sleep log"
                items.append({
                    "type": "sleep",
                    "timestamp": ts,
                    "title": "Sleep",
                    "subtitle": subtitle,
                })
        except Exception:
            pass

        try:
            # Todos/reminders: show items created in range (timestamp) + completions in range (completed_at)
            start_ts = f"{start_date}T00:00:00"
            end_ts = f"{end_date}T23:59:59.999999"
            q = supabase.table("reminders_todos").select("*").eq("user_id", uid)\
                .gte("timestamp", start_ts).lte("timestamp", end_ts).order("timestamp", desc=True).limit(200)
            res = q.execute()
            for log in (res.data or []):
                ts = _safe_iso(log.get('timestamp'))
                ttype = (log.get('type') or 'todo')
                title = "Reminder" if ttype == 'reminder' else "Todo"
                content = (log.get('content') or '').strip()
                items.append({
                    "type": ttype,
                    "timestamp": ts,
                    "title": title,
                    "subtitle": content or title,
                })
        except Exception:
            pass

        if metric == 'messages' or metric == '':
            try:
                start_ts = f"{start_date}T00:00:00"
                end_ts = f"{end_date}T23:59:59.999999"
                res = supabase.table("message_log").select("processed_at,message_body").eq("user_id", uid)\
                    .gte("processed_at", start_ts).lte("processed_at", end_ts).order("processed_at", desc=True).limit(200).execute()
                for m in (res.data or []):
                    ts = _safe_iso(m.get("processed_at"))
                    body = (m.get("message_body") or "").strip()
                    items.append({
                        "type": "message",
                        "timestamp": ts,
                        "title": "Message to Alfred",
                        "subtitle": body[:140] if body else "Message",
                    })
            except Exception:
                pass

        items = [it for it in items if _metric_allows(it.get("type") or "")]
        items.sort(key=lambda it: _dt_key(it.get("timestamp")), reverse=True)
        items = items[:200]

        return jsonify({
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "items": items,
        })

    @app.route('/dashboard/api/trends/series')
    @require_login
    def dashboard_api_trends_series():
        """
        Time-series data for Trends chart (Core/Pro).
        Query params:
        - timeframe: '7d' | '14d' | '1m' | '1y'
        - metric: 'sleep' | 'water' | 'calories' | 'protein' | 'carbs' | 'fat' | 'todos' | 'workouts' | 'messages'
        """
        from datetime import date, timedelta, datetime
        from calendar import month_abbr, monthrange

        user = auth_manager.get_current_user()
        plan = normalize_plan(user.get("plan"))
        if not can_use_feature(plan, "trends"):
            return jsonify({"success": False, "error": "Trends require Core or Pro."}), 403
        tf = (request.args.get('timeframe') or '7d').strip()
        metric = (request.args.get('metric') or 'calories').strip()

        if metric not in TRENDS_ALLOWED_METRICS:
            return jsonify({'success': False, 'error': 'Invalid metric'}), 400

        days = TRENDS_TF_DAYS.get(tf, 7)
        if tf not in TRENDS_TF_DAYS:
            tf = '7d'

        end_d = date.today()
        start_d = end_d - timedelta(days=days - 1)

        def _safe_dt(s: str):
            if not s:
                return None
            try:
                s2 = str(s).replace(" ", "T").replace("Z", "+00:00")
                if len(s2) == 10:
                    s2 += "T00:00:00"
                return datetime.fromisoformat(s2)
            except Exception:
                return None

        def _series_value(s, metric):
            """Extract series value(s) from a day's stats. Returns float, or (workouts, exercises) for metric 'workouts'."""
            s = s or {}
            g = s.get('gym') or {}
            f = s.get('food') or {}
            if metric == 'sleep':
                return float((s.get('sleep') or {}).get('total_hours') or 0)
            if metric == 'water':
                return float((s.get('water') or {}).get('total_ml') or 0)
            if metric == 'calories':
                return float(f.get('total_calories') or 0)
            if metric == 'protein':
                return float(f.get('total_protein') or 0)
            if metric == 'carbs':
                return float(f.get('total_carbs') or 0)
            if metric == 'fat':
                return float(f.get('total_fat') or 0)
            if metric == 'todos':
                return float((s.get('todos') or {}).get('completed') or 0)
            if metric == 'workouts':
                return (float(g.get('workout_count') or 0), float(g.get('exercise_count') or 0))
            return 0.0

        # Preload message counts if needed
        msg_counts_by_date = {}
        msg_counts_by_month = {}
        if metric == 'messages':
            try:
                start_ts = f"{start_d.isoformat()}T00:00:00"
                end_ts = f"{end_d.isoformat()}T23:59:59.999999"
                res = supabase.table("message_log").select("processed_at").eq("user_id", int(user["id"]))\
                    .gte("processed_at", start_ts).lte("processed_at", end_ts).execute()
                for r in (res.data or []):
                    dt = _safe_dt(r.get("processed_at"))
                    if not dt:
                        continue
                    dkey = dt.date().isoformat()
                    msg_counts_by_date[dkey] = msg_counts_by_date.get(dkey, 0) + 1
                    mkey = f"{dt.year:04d}-{dt.month:02d}"
                    msg_counts_by_month[mkey] = msg_counts_by_month.get(mkey, 0) + 1
            except Exception:
                pass

        # 1y uses 12 monthly buckets; fetch full year in bulk then aggregate by month
        if tf == '1y':
            labels = []
            values = []
            values_workouts = []
            values_exercises = []
            # last 12 months inclusive
            y = end_d.year
            m = end_d.month
            months = []
            for _ in range(12):
                months.append((y, m))
                m -= 1
                if m == 0:
                    m = 12
                    y -= 1
            months.reverse()

            if metric != 'messages':
                year_start_d = end_d - timedelta(days=364)
                by_date_1y = dashboard_data.get_series_bulk(int(user["id"]), year_start_d.isoformat(), end_d.isoformat())

            for (yy, mm) in months:
                labels.append(f"{month_abbr[mm]} {yy}")
                if metric == 'messages':
                    values.append(int(msg_counts_by_month.get(f"{yy:04d}-{mm:02d}", 0)))
                    continue

                total = 0.0
                total_workouts = 0.0
                total_exercises = 0.0
                try:
                    last_day = monthrange(yy, mm)[1]
                    for day in range(1, last_day + 1):
                        v = _series_value(by_date_1y.get(date(yy, mm, day).isoformat()), metric)
                        if metric == 'workouts':
                            total_workouts += v[0]
                            total_exercises += v[1]
                        else:
                            total += v
                    if metric == 'workouts':
                        values_workouts.append(total_workouts)
                        values_exercises.append(total_exercises)
                    else:
                        values.append(total)
                except Exception:
                    if metric == 'workouts':
                        values_workouts.append(0)
                        values_exercises.append(0)
                    else:
                        values.append(0)

            if metric == 'workouts':
                return jsonify({"success": True, "timeframe": tf, "metric": metric, "labels": labels, "values_workouts": values_workouts, "values_exercises": values_exercises})
            return jsonify({"success": True, "timeframe": tf, "metric": metric, "labels": labels, "values": values})

        # day-based series (bulk: one range query per data type instead of N×get_date_stats)
        by_date = dashboard_data.get_series_bulk(int(user["id"]), start_d.isoformat(), end_d.isoformat())
        labels = []
        values = []
        values_workouts = []
        values_exercises = []
        for i in range(days):
            d = start_d + timedelta(days=i)
            d_iso = d.isoformat()
            labels.append(d_iso)
            if metric == 'messages':
                values.append(int(msg_counts_by_date.get(d_iso, 0)))
                continue
            v = _series_value(by_date.get(d_iso), metric)
            if metric == 'workouts':
                values_workouts.append(v[0])
                values_exercises.append(v[1])
            else:
                values.append(v)

        if metric == 'workouts':
            return jsonify({"success": True, "timeframe": tf, "metric": metric, "labels": labels, "values_workouts": values_workouts, "values_exercises": values_exercises})
        return jsonify({"success": True, "timeframe": tf, "metric": metric, "labels": labels, "values": values})
    
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
        user = auth_manager.get_current_user()
        return render_template('dashboard/test.html', user=user, active_page='test_jobs')
    
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

            elif job_name == 'weekly_digest_due':
                if not notification_service:
                    return jsonify({'error': 'Notification service not available'}), 500
                notification_service.send_weekly_digest_due()
                return jsonify({'success': True, 'message': 'Weekly digest (due check) triggered'})

            elif job_name == 'morning_checkins':
                if not notification_service:
                    return jsonify({'error': 'Notification service not available'}), 500
                notification_service.send_morning_checkins_due()
                return jsonify({'success': True, 'message': 'Morning check-in (due check) triggered'})
            
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
