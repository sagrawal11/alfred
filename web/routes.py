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
                        job_scheduler=None, reminder_service=None, sync_service=None, notification_service=None,
                        limiter=None):
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
            success, user, error = auth_manager.register_with_email_password(email, password, name, phone_number, timezone=timezone or None)
            
            if success:
                # Phone verification disabled for now; go straight to dashboard.
                return jsonify({
                    'success': True,
                    'message': 'Registration successful!',
                    'redirect': url_for('dashboard_index')
                }), 200
            else:
                return jsonify({'error': error or 'Registration failed'}), 400
        
        # GET request - redirect to landing page (modals are there)
        return redirect(url_for('landing_page'))
    
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
        try:
            from data import UserPreferencesRepository
            prefs_repo = UserPreferencesRepository(supabase)
            prefs = prefs_repo.ensure(user['id']) if user else {}
        except Exception:
            prefs = {}
        return render_template('dashboard/settings.html', user=user, prefs=prefs)

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
            response_text = processor.process_message(message, phone_number=phone_number, user_id=user['id'])
            
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
        Delete an uploaded image and its metadata (privacy cleanup).
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
