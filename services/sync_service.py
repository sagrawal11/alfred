"""
Sync Service
Handles periodic synchronization of third-party integrations
"""

import logging
from typing import Any, Dict, List

from supabase import Client

from config import Config
from integrations import SyncManager

logger = logging.getLogger(__name__)


class SyncService:
    """Service for managing periodic integration syncs"""
    
    def __init__(self, supabase: Client, config: Config, sync_manager: SyncManager):
        self.supabase = supabase
        self.config = config
        self.sync_manager = sync_manager
    
    def sync_all_integrations(self):
        """Sync all active integrations for all users"""
        try:
            # Get all active integration connections
            result = self.supabase.table('integration_connections')\
                .select("*")\
                .eq('is_active', True)\
                .execute()
            
            connections = result.data if result.data else []
            
            if not connections:
                logger.debug("No active integrations to sync")
                return
            
            logger.info(f"Syncing {len(connections)} active integration(s)")
            
            for connection in connections:
                try:
                    user_id = connection.get('user_id')
                    provider = connection.get('provider')
                    
                    logger.info(f"Syncing {provider} for user {user_id}")
                    
                    # Use sync_manager to perform sync
                    sync_result = self.sync_manager.sync_integration(
                        user_id=user_id,
                        provider=provider
                    )
                    
                    if sync_result.status.value == 'success':
                        logger.info(f"Successfully synced {provider} for user {user_id}: {sync_result.items_synced} items")
                    else:
                        logger.warning(f"Sync failed for {provider} (user {user_id}): {sync_result.error}")
                
                except Exception as e:
                    logger.error(f"Error syncing integration {connection.get('id')}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in sync_all_integrations: {e}")
    
    def sync_user_integrations(self, user_id: int):
        """Sync all integrations for a specific user"""
        try:
            result = self.supabase.table('integration_connections')\
                .select("*")\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .execute()
            
            connections = result.data if result.data else []
            
            for connection in connections:
                provider = connection.get('provider')
                sync_result = self.sync_manager.sync_integration(
                    user_id=user_id,
                    provider=provider
                )
                
                if sync_result.status.value == 'success':
                    logger.info(f"Synced {provider} for user {user_id}")
                else:
                    logger.warning(f"Sync failed for {provider}: {sync_result.error}")
        
        except Exception as e:
            logger.error(f"Error syncing integrations for user {user_id}: {e}")
