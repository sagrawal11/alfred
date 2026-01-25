"""
Session Management
Manages user sessions and conversation state
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from supabase import Client


class SessionManager:
    """Manages user sessions and temporary state"""
    
    def __init__(self, supabase: Client):
        """
        Initialize session manager
        
        Args:
            supabase: Supabase client
        """
        self.supabase = supabase
        # In-memory session storage (could be moved to Redis in production)
        self.sessions: Dict[str, Dict] = {}
        # Session timeout (30 minutes)
        self.session_timeout = timedelta(minutes=30)
    
    def get_session(self, user_id: int) -> Dict:
        """
        Get or create a session for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Session dictionary
        """
        session_key = str(user_id)
        
        # Check if session exists and is still valid
        if session_key in self.sessions:
            session = self.sessions[session_key]
            if datetime.now() - session.get('last_activity', datetime.now()) < self.session_timeout:
                session['last_activity'] = datetime.now()
                return session
        
        # Create new session
        session = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'pending_confirmations': {},
            'pending_selections': {},
            'conversation_history': [],
            'context': {}
        }
        
        self.sessions[session_key] = session
        return session
    
    def update_session(self, user_id: int, updates: Dict):
        """
        Update session data
        
        Args:
            user_id: User ID
            updates: Dictionary of updates to apply
        """
        session = self.get_session(user_id)
        session.update(updates)
        session['last_activity'] = datetime.now()
    
    def clear_session(self, user_id: int):
        """
        Clear a user's session
        
        Args:
            user_id: User ID
        """
        session_key = str(user_id)
        if session_key in self.sessions:
            del self.sessions[session_key]
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired_keys = [
            key for key, session in self.sessions.items()
            if now - session.get('last_activity', datetime.now()) >= self.session_timeout
        ]
        for key in expired_keys:
            del self.sessions[key]
