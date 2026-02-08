"""
Authentication Manager
Handles user authentication, registration, password reset, and phone verification
Uses Supabase Auth for authentication with hybrid approach (links to custom users table)
"""

import os
from datetime import datetime
from typing import Dict, Optional, Tuple

from flask import session
from supabase import Client, create_client

from config import Config
from data import UserPreferencesRepository, UserRepository


class AuthManager:
    """Manages user authentication and registration using Supabase Auth"""
    
    def __init__(self, supabase: Client):
        """
        Initialize authentication manager
        
        Args:
            supabase: Supabase client (should use service role key for admin operations)
        """
        self.supabase = supabase
        self.user_repo = UserRepository(supabase)
        self.user_prefs_repo = UserPreferencesRepository(supabase)
        self.config = Config()
        
        # Create Supabase client for auth operations
        # Use anon key for standard auth operations (sign_up, sign_in)
        # Service role key would be needed for admin operations only
        self.auth_client = create_client(
            self.config.SUPABASE_URL,
            self.config.SUPABASE_KEY  # Anon key works for sign_up/sign_in
        )
    
    def register_with_email_password(self, email: str, password: str, name: str,
                                     phone_number: str, timezone: Optional[str] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Register a new user with email and password using Supabase Auth
        
        Args:
            email: User email
            password: User password
            name: User's name (required)
            phone_number: Phone number in E.164 format (required)
            
        Returns:
            Tuple of (success, user_dict, error_message)
        """
        # Validate required fields
        if not name or not name.strip():
            return False, None, "Name is required"
        
        if not phone_number or not phone_number.strip():
            return False, None, "Phone number is required"
        
        # Validate phone number format (E.164)
        import re
        phone_regex = re.compile(r'^\+[1-9]\d{1,14}$')
        if not phone_regex.match(phone_number.strip()):
            return False, None, "Phone number must be in E.164 format (e.g., +1234567890)"
        
        phone_number = phone_number.strip()
        name = name.strip()
        
        # Check if email already exists in custom users table
        existing = self.user_repo.get_by_email(email)
        if existing:
            return False, None, "Email already registered"
        
        # Check if phone number already exists
        existing_phone = self.user_repo.get_by_phone(phone_number)
        if existing_phone:
            return False, None, "Phone number already registered"
        
        try:
            # Create user in Supabase Auth with email and password
            # Include phone and name in metadata
            auth_response = self.auth_client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "phone_number": phone_number
                    }
                }
            })
            
            if not auth_response.user:
                return False, None, "Failed to create user in Supabase Auth"
            
            auth_user_id = auth_response.user.id
            
            # Create corresponding record in custom users table
            user = self.user_repo.create_user(
                phone_number=phone_number,
                email=email,
                password_hash=None,  # No longer needed - Supabase Auth handles passwords
                name=name,
                timezone=timezone or 'UTC',
                auth_user_id=auth_user_id
            )

            # Ensure user preferences row exists
            self.user_prefs_repo.ensure(user['id'])

            # When Confirm email is enabled, Supabase returns no session until the user confirms.
            # Do not set session so they must confirm before logging in.
            if auth_response.session:
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user.get('name')
                session['auth_user_id'] = auth_user_id
                session['access_token'] = auth_response.session.access_token
                session['refresh_token'] = auth_response.session.refresh_token
                return True, user, None

            # No session: email confirmation required
            user_with_flag = dict(user)
            user_with_flag['email_confirmation_required'] = True
            return True, user_with_flag, None
            
        except Exception as e:
            error_msg = str(e)
            # Handle Supabase Auth specific errors
            if "User already registered" in error_msg or "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                return False, None, "Email or phone number already registered"
            return False, None, f"Registration failed: {error_msg}"
    
    def send_phone_otp(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Send phone verification OTP via Supabase Auth
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate phone number format
            import re
            phone_regex = re.compile(r'^\+[1-9]\d{1,14}$')
            if not phone_regex.match(phone_number.strip()):
                return False, "Phone number must be in E.164 format (e.g., +1234567890)"
            
            # Send OTP via Supabase Auth
            response = self.auth_client.auth.sign_in_with_otp({
                "phone": phone_number.strip()
            })
            
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                return False, "Too many requests. Please wait before requesting another code."
            return False, f"Failed to send verification code: {error_msg}"
    
    def verify_phone_otp(self, phone_number: str, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify phone OTP and sign in user
        
        Args:
            phone_number: Phone number in E.164 format
            token: OTP code received via SMS
            
        Returns:
            Tuple of (success, user_dict, error_message)
        """
        try:
            # Verify OTP with Supabase Auth
            response = self.auth_client.auth.verify_otp({
                "phone": phone_number.strip(),
                "token": token.strip()
            })
            
            if not response.user:
                return False, None, "Invalid verification code"
            
            auth_user_id = response.user.id
            
            # Get or create user in custom users table
            user = self.user_repo.get_by_auth_user_id(auth_user_id)
            
            if not user:
                # Create user record if it doesn't exist
                # This can happen if user was created via phone OTP directly
                user = self.user_repo.create_user(
                    phone_number=phone_number.strip(),
                    email=response.user.email,
                    password_hash=None,
                    name=response.user.user_metadata.get('name', ''),
                    auth_user_id=auth_user_id
                )

            # Ensure user preferences row exists
            self.user_prefs_repo.ensure(user['id'])
            
            # Store user in session
            session['user_id'] = user['id']
            session['user_email'] = user.get('email')
            session['user_name'] = user.get('name')
            session['auth_user_id'] = auth_user_id
            if response.session:
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token
            
            # Update last login
            self.user_repo.update_last_login(user['id'])
            
            return True, user, None
            
        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
                return False, None, "Invalid or expired verification code"
            return False, None, f"Verification failed: {error_msg}"
    
    def login_with_email_password(self, email: str, password: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Authenticate a user with email and password using Supabase Auth
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (success, user_dict, error_message)
        """
        try:
            # Sign in with Supabase Auth
            response = self.auth_client.auth.sign_in_with_password({
                "email": email.strip(),
                "password": password
            })
            
            if not response.user:
                return False, None, "Invalid email or password"
            
            auth_user_id = response.user.id
            
            # Get user from custom users table
            user = self.user_repo.get_by_auth_user_id(auth_user_id)
            
            if not user:
                # User exists in Supabase Auth but not in custom table
                # This shouldn't happen, but handle it gracefully
                return False, None, "User account not properly set up. Please contact support."
            
            # Check if account is active
            if not user.get('is_active', True):
                return False, None, "Account is deactivated"
            
            # Store user in session
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user.get('name')
            session['auth_user_id'] = auth_user_id
            if response.session:
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token
            
            # Update last login
            self.user_repo.update_last_login(user['id'])
            
            return True, user, None
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid login credentials" in error_msg or "invalid" in error_msg.lower():
                return False, None, "Invalid email or password"
            return False, None, f"Login failed: {error_msg}"
    
    def request_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Request password reset via Supabase Auth.
        Sends an email with a link that redirects to our reset-password page.

        Args:
            email: User email

        Returns:
            Tuple of (success, error_message)
        """
        try:
            base_url = (self.config.BASE_URL or "").rstrip("/")
            redirect_to = f"{base_url}/dashboard/reset-password" if base_url else None
            options = {}
            if redirect_to:
                options["redirect_to"] = redirect_to
            self.auth_client.auth.reset_password_for_email(
                email.strip(), options=options if options else None
            )
            return True, None
        except Exception as e:
            return True, None
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset password using recovery token from Supabase Auth.
        The recovery flow is handled client-side: the email link redirects with
        tokens in the URL hash, and the reset page uses Supabase JS to set session
        and call updateUser({ password }). This server method is kept for API
        compatibility but the primary flow does not use it.

        Args:
            token: Password reset token (unused in client-side flow)
            new_password: New password

        Returns:
            Tuple of (success, error_message)
        """
        return False, "Please use the link from your email to reset your password on the reset page."
    
    def logout(self):
        """Log out current user"""
        try:
            # Sign out from Supabase Auth
            self.auth_client.auth.sign_out()
        except:
            pass
        finally:
            # Clear Flask session
            session.clear()
    
    def get_current_user(self) -> Optional[Dict]:
        """
        Get current logged-in user
        
        Returns:
            User dict or None if not logged in
        """
        user_id = session.get('user_id')
        if not user_id:
            return None
        
        # For now, trust Flask session (can add token verification later if needed)
        # In production, you might want to verify the Supabase JWT token
        user = self.user_repo.get_by_id(user_id)
        
        # Check if account is still active
        if user and not user.get('is_active', True):
            session.clear()
            return None
        
        return user
    
    def require_auth(self) -> Optional[Dict]:
        """
        Require authentication (decorator helper)
        
        Returns:
            User dict if authenticated, None otherwise
        """
        return self.get_current_user()
    
    # Legacy methods for backward compatibility
    def register(self, email: str, password: str, name: str, phone_number: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Legacy method - redirects to new registration method"""
        return self.register_with_email_password(email, password, name, phone_number)
    
    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Legacy method - redirects to new login method"""
        return self.login_with_email_password(email, password)
    
    def send_phone_verification_code(self, user_id: int, phone_number: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Legacy method - Send phone verification code
        Now uses Supabase Auth OTP
        
        Args:
            user_id: User ID (not used, kept for compatibility)
            phone_number: Phone number to verify
            
        Returns:
            Tuple of (success, verification_code, error_message)
            Note: Code is None since Supabase handles it
        """
        success, error = self.send_phone_otp(phone_number)
        return success, None, error
    
    def verify_phone_code(self, user_id: int, code: str) -> Tuple[bool, Optional[str]]:
        """
        Legacy method - Verify phone code
        Now uses Supabase Auth OTP verification
        
        Note: This method needs phone_number, not just user_id and code
        For backward compatibility, we'll get phone from user_id first
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        phone_number = user.get('phone_number')
        if not phone_number:
            return False, "Phone number not found for user"
        
        success, user_dict, error = self.verify_phone_otp(phone_number, code)
        return success, error
