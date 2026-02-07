"""
Sync Manager
Orchestrates data syncing from all integration providers
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from supabase import Client

from data import GymRepository, IntegrationRepository, SleepRepository
from .auth import IntegrationAuthManager
from .base import BaseIntegration, SyncResult, SyncStatus


class SyncManager:
    """Manages syncing data from all connected integrations"""
    
    def __init__(self, supabase: Client, integration_repo: IntegrationRepository,
                 auth_manager: IntegrationAuthManager):
        """
        Initialize sync manager
        
        Args:
            supabase: Supabase client
            integration_repo: IntegrationRepository instance
            auth_manager: IntegrationAuthManager instance
        """
        self.supabase = supabase
        self.integration_repo = integration_repo
        self.auth_manager = auth_manager
        self.gym_repo = GymRepository(supabase)
        self.sleep_repo = SleepRepository(supabase)
    
    def sync_integration(self, connection_id: int, integration: BaseIntegration,
                        sync_type: str = 'incremental') -> SyncResult:
        """
        Sync data from a specific integration
        
        Args:
            connection_id: Integration connection ID
            integration: Integration instance
            sync_type: Type of sync ('full', 'incremental', 'webhook')
            
        Returns:
            SyncResult with sync status
        """
        try:
            # Get connection
            connection = self.integration_repo.get_by_id(connection_id)
            if not connection or not connection.get('is_active'):
                return SyncResult(SyncStatus.ERROR, error_message="Connection not found or inactive")
            
            # Get valid access token
            access_token = self.auth_manager.get_valid_access_token(connection_id, integration)
            if not access_token:
                return SyncResult(SyncStatus.ERROR, error_message="Failed to get valid access token")
            
            # Get last sync time for incremental sync
            last_sync_at = None
            if sync_type == 'incremental' and connection.get('last_sync_at'):
                last_sync_at = datetime.fromisoformat(connection['last_sync_at'].replace('Z', '+00:00'))
            
            # Perform sync
            sync_result = integration.sync_data(
                access_token=access_token,
                user_id=connection['user_id'],
                last_sync_at=last_sync_at
            )
            
            # Process synced data
            if sync_result.status == SyncStatus.SUCCESS or sync_result.status == SyncStatus.PARTIAL:
                self._process_synced_data(connection_id, connection['user_id'], 
                                        integration.provider_name, sync_result.data)
            
            # Log sync
            self.integration_repo.log_sync(
                integration_id=connection_id,
                sync_type=sync_type,
                status=sync_result.status.value,
                items_synced=sync_result.items_synced,
                items_failed=sync_result.items_failed,
                error_message=sync_result.error_message
            )
            
            # Update last sync time
            if sync_result.status == SyncStatus.SUCCESS:
                self.integration_repo.update_last_sync(connection_id)
            
            return sync_result
            
        except Exception as e:
            # Log error
            self.integration_repo.log_sync(
                integration_id=connection_id,
                sync_type=sync_type,
                status=SyncStatus.ERROR.value,
                error_message=str(e)
            )
            return SyncResult(SyncStatus.ERROR, error_message=str(e))
    
    def _process_synced_data(self, connection_id: int, user_id: int, provider: str,
                            synced_items: List[Dict]):
        """
        Process and store synced data
        
        Args:
            connection_id: Integration connection ID
            user_id: User ID
            provider: Provider name
            synced_items: List of synced data items
        """
        for item in synced_items:
            try:
                # Check if we already have this item (deduplication)
                external_id = item.get('external_id')
                internal_type = item.get('internal_type')
                
                if external_id and internal_type:
                    existing = self.integration_repo.find_existing_mapping(
                        connection_id, external_id, internal_type
                    )
                    if existing:
                        # Already synced, skip
                        continue
                
                # Map external data to internal format
                internal_data = item.get('internal_data', {})
                
                # Store based on type
                if internal_type == 'gym_log':
                    gym_log = self.gym_repo.create_gym_log(
                        user_id=user_id,
                        exercise=internal_data.get('exercise', 'Unknown'),
                        sets=internal_data.get('sets', 1),
                        reps=internal_data.get('reps'),
                        weight=internal_data.get('weight'),
                        notes=internal_data.get('notes', f"Synced from {provider}")
                    )
                    
                    # Map external to internal
                    if external_id:
                        self.integration_repo.map_external_data(
                            connection_id, external_id, 'gym_log', gym_log['id'], item.get('external_data')
                        )
                
                elif internal_type == 'sleep_log':
                    sleep_log = self.sleep_repo.create_sleep_log(
                        user_id=user_id,
                        date=internal_data.get('date'),
                        sleep_time=internal_data.get('sleep_time'),
                        wake_time=internal_data.get('wake_time'),
                        duration_hours=internal_data.get('duration_hours')
                    )
                    
                    # Map external to internal
                    if external_id:
                        self.integration_repo.map_external_data(
                            connection_id, external_id, 'sleep_log', sleep_log['id'], item.get('external_data')
                        )
                
                # Add more types as needed (food, water, etc.)
                
            except Exception as e:
                print(f"Error processing synced item: {e}")
                continue
    
    def sync_all_user_integrations(self, user_id: int) -> Dict[str, SyncResult]:
        """
        Sync all active integrations for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping provider names to sync results
        """
        connections = self.integration_repo.get_user_connections(user_id)
        results = {}
        
        # Note: This requires integration instances to be passed in
        # For now, return empty dict - will be populated when integrations are implemented
        return results
    
    def sync_all_active_integrations(self, integrations: Dict[str, BaseIntegration]) -> Dict[str, Dict[str, SyncResult]]:
        """
        Sync all active integrations across all users
        
        Args:
            integrations: Dictionary mapping provider names to integration instances
            
        Returns:
            Dictionary mapping user_id -> provider -> sync result
        """
        # This would be called by a scheduled job
        # For now, return empty - will be implemented when scheduler is set up
        return {}
