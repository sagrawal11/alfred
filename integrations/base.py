"""
Base Integration Interface
Abstract base class for all third-party integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SyncStatus(Enum):
    """Sync operation status"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class IntegrationResult:
    """Result of an integration operation"""
    
    def __init__(self, success: bool, message: str = "", data: Optional[Dict] = None):
        self.success = success
        self.message = message
        self.data = data or {}


class SyncResult:
    """Result of a sync operation"""
    
    def __init__(self, status: SyncStatus, items_synced: int = 0, 
                 items_failed: int = 0, error_message: Optional[str] = None,
                 data: Optional[List[Dict]] = None):
        self.status = status
        self.items_synced = items_synced
        self.items_failed = items_failed
        self.error_message = error_message
        self.data = data or []


class BaseIntegration(ABC):
    """Abstract base class for all integrations"""
    
    def __init__(self, provider_name: str, client_id: str, client_secret: str,
                 redirect_uri: str):
        """
        Initialize integration
        
        Args:
            provider_name: Name of the provider (e.g., 'fitbit', 'google_calendar')
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
        """
        self.provider_name = provider_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    @abstractmethod
    def get_authorization_url(self, state: str, scopes: List[str]) -> str:
        """
        Generate OAuth authorization URL
        
        Args:
            state: CSRF protection state token
            scopes: List of OAuth scopes to request
            
        Returns:
            Authorization URL
        """
        pass
    
    @abstractmethod
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access/refresh tokens
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.
        """
        pass
    
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary with new access_token, refresh_token, expires_in
        """
        pass
    
    @abstractmethod
    def sync_data(self, access_token: str, user_id: int, 
                 last_sync_at: Optional[datetime] = None) -> SyncResult:
        """
        Sync data from the provider
        
        Args:
            access_token: Valid access token
            user_id: User ID in our system
            last_sync_at: Last successful sync timestamp (for incremental sync)
            
        Returns:
            SyncResult with sync status and data
        """
        pass
    
    @abstractmethod
    def map_external_to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map external provider data to internal schema
        
        Args:
            external_data: Data from provider API
            
        Returns:
            Mapped data in internal format
        """
        pass
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke access token (optional - not all providers support this)
        
        Args:
            token: Access token to revoke
            
        Returns:
            True if revoked successfully
        """
        # Default implementation - override if provider supports token revocation
        return True
