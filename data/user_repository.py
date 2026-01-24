"""
User Repository
Handles all user account operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import Client
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user accounts"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'users')
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user by phone number
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            User record or None if not found
        """
        result = self.client.table(self.table_name).select("*").eq("phone_number", phone_number).execute()
        if result.data:
            return result.data[0]
        return None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email
        
        Args:
            email: User email address
            
        Returns:
            User record or None if not found
        """
        result = self.client.table(self.table_name).select("*").eq("email", email).execute()
        if result.data:
            return result.data[0]
        return None
    
    def create_user(self, phone_number: str, email: Optional[str] = None, 
                   password_hash: Optional[str] = None, name: Optional[str] = None,
                   timezone: str = 'UTC') -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            phone_number: Phone number in E.164 format
            email: Email address (optional)
            password_hash: Bcrypt password hash (optional)
            name: User's name (optional)
            timezone: User's timezone (default: UTC)
            
        Returns:
            Created user record
        """
        data = {
            'phone_number': phone_number,
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'timezone': timezone,
            'is_active': True
        }
        return self.create(data)
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        self.update(user_id, {'last_login_at': datetime.now().isoformat()})
    
    def increment_failed_login(self, user_id: int):
        """Increment failed login attempts counter"""
        user = self.get_by_id(user_id)
        if user:
            failed_attempts = user.get('failed_login_attempts', 0) + 1
            update_data = {
                'failed_login_attempts': failed_attempts,
                'last_failed_login': datetime.now().isoformat()
            }
            
            # Lock account after 5 failed attempts (1 hour lockout)
            if failed_attempts >= 5:
                from datetime import timedelta
                update_data['locked_until'] = (datetime.now() + timedelta(hours=1)).isoformat()
            
            self.update(user_id, update_data)
    
    def reset_failed_login(self, user_id: int):
        """Reset failed login attempts counter"""
        self.update(user_id, {
            'failed_login_attempts': 0,
            'locked_until': None
        })
    
    def is_locked(self, user_id: int) -> bool:
        """Check if user account is locked"""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        locked_until = user.get('locked_until')
        if locked_until:
            locked_time = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
            if datetime.now() < locked_time:
                return True
            else:
                # Lock expired, reset it
                self.update(user_id, {'locked_until': None, 'failed_login_attempts': 0})
                return False
        
        return False
    
    def deactivate_user(self, user_id: int):
        """Deactivate a user account"""
        self.update(user_id, {'is_active': False})
    
    def activate_user(self, user_id: int):
        """Activate a user account"""
        self.update(user_id, {'is_active': True})
