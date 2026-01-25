"""
Authentication Manager
Handles user authentication, registration, password reset, and phone verification
"""

import os
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import session
import bcrypt
from supabase import Client

from data import UserRepository
from communication_service import CommunicationService


class AuthManager:
    """Manages user authentication and registration"""
    
    def __init__(self, supabase: Client):
        """
        Initialize authentication manager
        
        Args:
            supabase: Supabase client
        """
        self.supabase = supabase
        self.user_repo = UserRepository(supabase)
        self.communication_service = CommunicationService()
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hash
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password
            password_hash: Bcrypt hash
            
        Returns:
            True if password matches
        """
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Authenticate a user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (success, user_dict, error_message)
        """
        user = self.user_repo.get_by_email(email)
        
        if not user:
            return False, None, "Invalid email or password"
        
        if not user.get('password_hash'):
            return False, None, "Account not set up. Please register first."
        
        if not self.verify_password(password, user['password_hash']):
            # Increment failed login attempts
            self.user_repo.increment_failed_login(user['id'])
            return False, None, "Invalid email or password"
        
        # Check if account is locked
        if user.get('failed_login_attempts', 0) >= 5:
            return False, None, "Account locked due to too many failed login attempts"
        
        # Reset failed login attempts on successful login
        self.user_repo.reset_failed_login(user['id'])
        self.user_repo.update_last_login(user['id'])
        
        # Store user in session
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_name'] = user.get('name')
        
        return True, user, None
    
    def register(self, email: str, password: str, name: Optional[str] = None,
                phone_number: Optional[str] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Register a new user
        
        Args:
            email: User email
            password: User password
            name: User's name (optional)
            phone_number: Phone number (optional)
            
        Returns:
            Tuple of (success, user_dict, error_message)
        """
        # Check if email already exists
        existing = self.user_repo.get_by_email(email)
        if existing:
            return False, None, "Email already registered"
        
        # Check if phone number already exists (if provided)
        if phone_number:
            existing_phone = self.user_repo.get_by_phone(phone_number)
            if existing_phone:
                return False, None, "Phone number already registered"
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Schema requires unique non-null phone_number. Use placeholder for web-only signup.
        import uuid
        effective_phone = (phone_number or '').strip()
        if not effective_phone:
            effective_phone = f"web-{uuid.uuid4().hex[:12]}"
        
        # Create user
        try:
            user = self.user_repo.create_user(
                phone_number=effective_phone,
                email=email,
                password_hash=password_hash,
                name=name
            )
            
            # Store user in session
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user.get('name')
            
            return True, user, None
        except Exception as e:
            return False, None, f"Registration failed: {str(e)}"
    
    def send_phone_verification_code(self, user_id: int, phone_number: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send phone verification code via SMS
        
        Args:
            user_id: User ID
            phone_number: Phone number to verify
            
        Returns:
            Tuple of (success, verification_code, error_message)
            Returns code for testing purposes
        """
        # Generate 6-digit code
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store verification code in database (with expiration)
        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        try:
            # Update user with verification code
            self.user_repo.update(user_id, {
                'phone_verification_code': code,
                'phone_verification_expires_at': expires_at
            })
            
            # Send SMS
            message = f"Your verification code is: {code}. It expires in 10 minutes."
            result = self.communication_service.send_response(message, phone_number)
            
            if result.get('success'):
                return True, code, None  # Return code for testing
            else:
                return False, code, "Failed to send SMS. Code generated but not sent."
        except Exception as e:
            return False, None, f"Failed to send verification code: {str(e)}"
    
    def verify_phone_code(self, user_id: int, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify phone verification code
        
        Args:
            user_id: User ID
            code: Verification code
            
        Returns:
            Tuple of (success, error_message)
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        stored_code = user.get('phone_verification_code')
        expires_at_str = user.get('phone_verification_expires_at')
        
        if not stored_code:
            return False, "No verification code found. Please request a new one."
        
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                return False, "Verification code expired. Please request a new one."
        
        if stored_code != code:
            return False, "Invalid verification code"
        
        # Mark phone as verified
        self.user_repo.update(user_id, {
            'phone_verified': True,
            'phone_verification_code': None,
            'phone_verification_expires_at': None
        })
        
        return True, None
    
    def request_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Request password reset (sends email with reset link)
        
        Args:
            email: User email
            
        Returns:
            Tuple of (success, error_message)
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True, None
        
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # Store reset token
        self.user_repo.update(user['id'], {
            'password_reset_token': token,
            'password_reset_expires_at': expires_at
        })
        
        # TODO: Send email with reset link
        # For now, return token for testing
        reset_url = f"/dashboard/reset-password?token={token}"
        print(f"Password reset token for {email}: {token}")
        print(f"Reset URL: {reset_url}")
        
        return True, None
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset password using token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find user by reset token
        result = self.supabase.table('users')\
            .select('*')\
            .eq('password_reset_token', token)\
            .execute()
        
        if not result.data:
            return False, "Invalid or expired reset token"
        
        user = result.data[0]
        expires_at_str = user.get('password_reset_expires_at')
        
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                return False, "Reset token expired"
        
        # Update password
        password_hash = self.hash_password(new_password)
        self.user_repo.update(user['id'], {
            'password_hash': password_hash,
            'password_reset_token': None,
            'password_reset_expires_at': None
        })
        
        return True, None
    
    def logout(self):
        """Log out current user"""
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
        
        return self.user_repo.get_by_id(user_id)
    
    def require_auth(self) -> Optional[Dict]:
        """
        Require authentication (decorator helper)
        
        Returns:
            User dict if authenticated, None otherwise
        """
        return self.get_current_user()
