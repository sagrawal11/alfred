"""
Integration Repository
Handles storage and retrieval of integration connections and sync history
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import Client
from .base_repository import BaseRepository


class IntegrationRepository(BaseRepository):
    """Repository for user integrations"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'user_integrations')
    
    def create_connection(self, user_id: int, provider: str, 
                         access_token: str, refresh_token: Optional[str] = None,
                         provider_user_id: Optional[str] = None,
                         token_expires_at: Optional[datetime] = None,
                         scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new integration connection
        
        Args:
            user_id: User ID
            provider: Provider name ('fitbit', 'google_calendar', etc.)
            access_token: Encrypted access token
            refresh_token: Encrypted refresh token (optional)
            provider_user_id: User's ID in provider system (optional)
            token_expires_at: Token expiration timestamp (optional)
            scopes: List of granted scopes (optional)
            
        Returns:
            Created connection record
        """
        data = {
            'user_id': user_id,
            'provider': provider,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'provider_user_id': provider_user_id,
            'token_expires_at': token_expires_at.isoformat() if token_expires_at else None,
            'scopes': scopes or [],
            'is_active': True
        }
        
        # Use upsert to handle existing connections
        result = self.client.table(self.table_name)\
            .upsert(data, on_conflict='user_id,provider')\
            .execute()
        
        if result.data:
            return result.data[0]
        raise Exception("Failed to create integration connection")
    
    def get_connection(self, user_id: int, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get integration connection for a user
        
        Args:
            user_id: User ID
            provider: Provider name
            
        Returns:
            Connection record or None if not found
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("provider", provider)\
            .eq("is_active", True)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def get_user_connections(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all active connections for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of connection records
        """
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()
        
        return result.data if result.data else []
    
    def update_tokens(self, connection_id: int, access_token: Optional[str] = None,
                     refresh_token: Optional[str] = None,
                     token_expires_at: Optional[datetime] = None):
        """
        Update tokens for a connection
        
        Args:
            connection_id: Connection ID
            access_token: New access token (optional)
            refresh_token: New refresh token (optional)
            token_expires_at: New expiration time (optional)
        """
        update_data = {}
        if access_token is not None:
            update_data['access_token'] = access_token
        if refresh_token is not None:
            update_data['refresh_token'] = refresh_token
        if token_expires_at is not None:
            update_data['token_expires_at'] = token_expires_at.isoformat()
        
        if update_data:
            self.update(connection_id, update_data)
    
    def update_last_sync(self, connection_id: int):
        """Update last sync timestamp"""
        self.update(connection_id, {'last_sync_at': datetime.now().isoformat()})
    
    def deactivate_connection(self, connection_id: int):
        """Deactivate a connection"""
        self.update(connection_id, {'is_active': False})
    
    def log_sync(self, integration_id: int, sync_type: str, status: str,
                 items_synced: int = 0, items_failed: int = 0,
                 error_message: Optional[str] = None) -> int:
        """
        Log a sync operation
        
        Args:
            integration_id: Integration connection ID
            sync_type: Type of sync ('full', 'incremental', 'webhook')
            status: Sync status ('success', 'error', 'partial')
            items_synced: Number of items synced
            items_failed: Number of items that failed
            error_message: Error message if failed
            
        Returns:
            Sync history record ID
        """
        data = {
            'integration_id': integration_id,
            'sync_type': sync_type,
            'status': status,
            'items_synced': items_synced,
            'items_failed': items_failed,
            'error_message': error_message,
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat()
        }
        
        result = self.client.table('sync_history').insert(data).execute()
        if result.data:
            return result.data[0]['id']
        raise Exception("Failed to log sync")
    
    def get_sync_history(self, integration_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sync history for an integration
        
        Args:
            integration_id: Integration connection ID
            limit: Maximum number of records to return
            
        Returns:
            List of sync history records
        """
        result = self.client.table('sync_history')\
            .select("*")\
            .eq("integration_id", integration_id)\
            .order("started_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data if result.data else []
    
    def map_external_data(self, integration_id: int, external_id: str,
                         internal_type: str, internal_id: int,
                         external_data: Optional[Dict] = None):
        """
        Map external data ID to internal ID
        
        Args:
            integration_id: Integration connection ID
            external_id: External system's ID
            internal_type: Internal data type ('gym_log', 'sleep_log', etc.)
            internal_id: Internal record ID
            external_data: Snapshot of external data (optional)
        """
        data = {
            'integration_id': integration_id,
            'external_id': external_id,
            'internal_type': internal_type,
            'internal_id': internal_id,
            'external_data': external_data,
            'last_synced_at': datetime.now().isoformat()
        }
        
        # Use upsert to handle duplicates
        self.client.table('external_data_mapping')\
            .upsert(data, on_conflict='integration_id,external_id,internal_type')\
            .execute()
    
    def find_existing_mapping(self, integration_id: int, external_id: str,
                             internal_type: str) -> Optional[Dict[str, Any]]:
        """
        Find existing mapping for external data
        
        Args:
            integration_id: Integration connection ID
            external_id: External system's ID
            internal_type: Internal data type
            
        Returns:
            Mapping record or None if not found
        """
        result = self.client.table('external_data_mapping')\
            .select("*")\
            .eq("integration_id", integration_id)\
            .eq("external_id", external_id)\
            .eq("internal_type", internal_type)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
