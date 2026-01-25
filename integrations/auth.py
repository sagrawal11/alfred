"""
Integration Auth Manager
Handles OAuth flows for all integration providers
"""

import os
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
import requests
from cryptography.fernet import Fernet

from .base import BaseIntegration
from data import IntegrationRepository


class IntegrationAuthManager:
    """Manages OAuth authentication for integrations"""
    
    def __init__(self, supabase, integration_repo: IntegrationRepository):
        """
        Initialize auth manager
        
        Args:
            supabase: Supabase client
            integration_repo: IntegrationRepository instance
        """
        self.supabase = supabase
        self.integration_repo = integration_repo
        
        # Get encryption key for tokens
        encryption_key = os.getenv('ENCRYPTION_KEY', '')
        if encryption_key:
            try:
                self.cipher = Fernet(encryption_key.encode())
            except Exception:
                # If key is invalid, generate a warning but continue
                print("Warning: ENCRYPTION_KEY invalid, tokens will be stored unencrypted")
                self.cipher = None
        else:
            print("Warning: ENCRYPTION_KEY not set, tokens will be stored unencrypted")
            self.cipher = None
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for storage"""
        if self.cipher:
            return self.cipher.encrypt(token.encode()).decode()
        return token  # Store unencrypted if no key
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a stored token"""
        if self.cipher:
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        return encrypted_token  # Return as-is if not encrypted
    
    def generate_state(self) -> str:
        """Generate CSRF protection state token"""
        return secrets.token_urlsafe(32)
    
    def initiate_oauth(self, user_id: int, provider: str, 
                      integration: BaseIntegration, scopes: list) -> Tuple[str, str]:
        """
        Initiate OAuth flow
        
        Args:
            user_id: User ID
            provider: Provider name
            integration: Integration instance
            scopes: List of OAuth scopes
            
        Returns:
            Tuple of (authorization_url, state_token)
        """
        state = self.generate_state()
        
        # Store state in session or database (for verification)
        # For now, we'll verify state in callback
        auth_url = integration.get_authorization_url(state, scopes)
        
        return auth_url, state
    
    def complete_oauth(self, user_id: int, provider: str,
                      integration: BaseIntegration, code: str,
                      state: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Complete OAuth flow by exchanging code for tokens
        
        Args:
            user_id: User ID
            provider: Provider name
            integration: Integration instance
            code: Authorization code
            state: State token (for verification)
            
        Returns:
            Tuple of (success, error_message, connection_data)
        """
        try:
            # Exchange code for tokens
            tokens = integration.exchange_code_for_tokens(code)
            
            if not tokens or 'access_token' not in tokens:
                return False, "Failed to obtain access token", None
            
            # Encrypt tokens
            encrypted_access = self.encrypt_token(tokens['access_token'])
            encrypted_refresh = self.encrypt_token(tokens.get('refresh_token', '')) if tokens.get('refresh_token') else None
            
            # Calculate expiration
            expires_at = None
            if 'expires_in' in tokens:
                from datetime import datetime, timedelta
                expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
            
            # Store connection
            connection = self.integration_repo.create_connection(
                user_id=user_id,
                provider=provider,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                provider_user_id=tokens.get('user_id'),
                token_expires_at=expires_at,
                scopes=tokens.get('scope', '').split() if isinstance(tokens.get('scope'), str) else tokens.get('scopes', [])
            )
            
            return True, None, connection
            
        except Exception as e:
            return False, f"OAuth completion failed: {str(e)}", None
    
    def refresh_tokens(self, connection_id: int, integration: BaseIntegration) -> Tuple[bool, Optional[str]]:
        """
        Refresh access token for a connection
        
        Args:
            connection_id: Connection ID
            integration: Integration instance
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            connection = self.integration_repo.get_by_id(connection_id)
            if not connection:
                return False, "Connection not found"
            
            refresh_token_encrypted = connection.get('refresh_token')
            if not refresh_token_encrypted:
                return False, "No refresh token available"
            
            # Decrypt refresh token
            refresh_token = self.decrypt_token(refresh_token_encrypted)
            
            # Refresh tokens
            new_tokens = integration.refresh_access_token(refresh_token)
            
            if not new_tokens or 'access_token' not in new_tokens:
                return False, "Failed to refresh access token"
            
            # Encrypt new tokens
            encrypted_access = self.encrypt_token(new_tokens['access_token'])
            encrypted_refresh = self.encrypt_token(new_tokens.get('refresh_token', refresh_token)) if new_tokens.get('refresh_token') else None
            
            # Calculate expiration
            expires_at = None
            if 'expires_in' in new_tokens:
                from datetime import datetime, timedelta
                expires_at = datetime.now() + timedelta(seconds=new_tokens['expires_in'])
            
            # Update connection
            self.integration_repo.update_tokens(
                connection_id,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                token_expires_at=expires_at
            )
            
            return True, None
            
        except Exception as e:
            return False, f"Token refresh failed: {str(e)}"
    
    def get_valid_access_token(self, connection_id: int, integration: BaseIntegration) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary
        
        Args:
            connection_id: Connection ID
            integration: Integration instance
            
        Returns:
            Valid access token or None if failed
        """
        connection = self.integration_repo.get_by_id(connection_id)
        if not connection:
            return None
        
        # Check if token is expired
        token_expires_at = connection.get('token_expires_at')
        if token_expires_at:
            from datetime import datetime
            expires = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
            if datetime.now() >= expires:
                # Token expired, refresh it
                success, error = self.refresh_tokens(connection_id, integration)
                if not success:
                    return None
                # Get updated connection
                connection = self.integration_repo.get_by_id(connection_id)
        
        # Decrypt and return access token
        encrypted_token = connection.get('access_token')
        if encrypted_token:
            return self.decrypt_token(encrypted_token)
        
        return None
