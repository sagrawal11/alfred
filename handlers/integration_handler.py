"""
Integration Handler
Handles SMS commands related to integrations
"""

from typing import Dict, Optional
from data import IntegrationRepository
from integrations import IntegrationAuthManager, SyncManager
from integrations.health.fitbit import FitbitIntegration
from integrations.calendar.google_calendar import GoogleCalendarIntegration
from responses.formatter import ResponseFormatter
import os


class IntegrationHandler:
    """Handles integration-related user commands"""
    
    def __init__(self, supabase, integration_repo: IntegrationRepository,
                 integration_auth: IntegrationAuthManager,
                 sync_manager: SyncManager,
                 formatter: ResponseFormatter):
        """
        Initialize integration handler
        
        Args:
            supabase: Supabase client
            integration_repo: IntegrationRepository instance
            integration_auth: IntegrationAuthManager instance
            sync_manager: SyncManager instance
            formatter: ResponseFormatter instance
        """
        self.supabase = supabase
        self.integration_repo = integration_repo
        self.integration_auth = integration_auth
        self.sync_manager = sync_manager
        self.formatter = formatter
    
    def handle(self, message: str, intent: str, entities: Dict, 
              user_id: int) -> Optional[str]:
        """
        Handle integration-related commands
        
        Args:
            message: User message
            intent: Classified intent
            entities: Extracted entities
            user_id: User ID
            
        Returns:
            Response message or None
        """
        message_lower = message.lower()
        
        # Check for integration commands
        if 'connect' in message_lower or 'link' in message_lower:
            return self._handle_connect(message_lower, user_id)
        
        elif 'sync' in message_lower or 'update' in message_lower:
            return self._handle_sync(message_lower, user_id)
        
        elif 'disconnect' in message_lower or 'unlink' in message_lower:
            return self._handle_disconnect(message_lower, user_id)
        
        elif 'integrations' in message_lower or 'connected' in message_lower:
            return self._handle_list_integrations(user_id)
        
        return None
    
    def _handle_connect(self, message: str, user_id: int) -> str:
        """Handle connect command"""
        # Detect provider
        provider = None
        if 'fitbit' in message:
            provider = 'fitbit'
        elif 'calendar' in message or 'google' in message:
            provider = 'google_calendar'
        elif 'fit' in message and 'google' in message:
            provider = 'google_fit'
        
        if not provider:
            return "Which integration would you like to connect? (Fitbit, Google Calendar, etc.)"
        
        # Generate connection URL
        # For SMS, we'll provide a link to the web dashboard
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        connect_url = f"{base_url}/dashboard/integrations/{provider}/connect"
        
        return f"To connect {provider}, visit: {connect_url}\n\nYou'll need to log in first if you haven't already."
    
    def _handle_sync(self, message: str, user_id: int) -> str:
        """Handle sync command"""
        # Detect provider
        provider = None
        if 'fitbit' in message:
            provider = 'fitbit'
        elif 'calendar' in message:
            provider = 'google_calendar'
        
        if provider:
            # Sync specific provider
            connection = self.integration_repo.get_connection(user_id, provider)
            if not connection:
                return f"You don't have {provider} connected. Connect it first!"
            
            integration = self._get_integration_instance(provider)
            if not integration:
                return f"Integration {provider} not available"
            
            sync_result = self.sync_manager.sync_integration(
                connection_id=connection['id'],
                integration=integration,
                sync_type='full'
            )
            
            if sync_result.status.value == 'success':
                return f"Synced {provider}! {sync_result.items_synced} items synced."
            else:
                return f"Sync failed: {sync_result.error_message}"
        else:
            # Sync all
            connections = self.integration_repo.get_user_connections(user_id)
            if not connections:
                return "You don't have any integrations connected."
            
            results = []
            for conn in connections:
                provider = conn['provider']
                integration = self._get_integration_instance(provider)
                if integration:
                    sync_result = self.sync_manager.sync_integration(
                        connection_id=conn['id'],
                        integration=integration,
                        sync_type='incremental'
                    )
                    results.append(f"{provider}: {sync_result.items_synced} items")
            
            if results:
                return "Synced all integrations:\n" + "\n".join(results)
            return "No integrations available to sync"
    
    def _handle_disconnect(self, message: str, user_id: int) -> str:
        """Handle disconnect command"""
        # Detect provider
        provider = None
        if 'fitbit' in message:
            provider = 'fitbit'
        elif 'calendar' in message:
            provider = 'google_calendar'
        
        if not provider:
            return "Which integration would you like to disconnect?"
        
        connection = self.integration_repo.get_connection(user_id, provider)
        if not connection:
            return f"You don't have {provider} connected."
        
        self.integration_repo.deactivate_connection(connection['id'])
        return f"{provider} disconnected successfully."
    
    def _handle_list_integrations(self, user_id: int) -> str:
        """List connected integrations"""
        connections = self.integration_repo.get_user_connections(user_id)
        
        if not connections:
            return "You don't have any integrations connected. Say 'connect fitbit' or 'connect calendar' to get started!"
        
        providers = [conn['provider'] for conn in connections]
        return f"Connected integrations: {', '.join(providers)}"
    
    def _get_integration_instance(self, provider: str):
        """Get integration instance for a provider"""
        if provider == 'fitbit':
            client_id = os.getenv('FITBIT_CLIENT_ID')
            client_secret = os.getenv('FITBIT_CLIENT_SECRET')
            redirect_uri = os.getenv('BASE_URL', 'http://localhost:5001') + f"/dashboard/integrations/fitbit/callback"
            
            if not client_id or not client_secret:
                return None
            
            return FitbitIntegration(client_id, client_secret, redirect_uri)
        
        elif provider == 'google_calendar':
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            redirect_uri = os.getenv('BASE_URL', 'http://localhost:5001') + f"/dashboard/integrations/google_calendar/callback"
            
            if not client_id or not client_secret:
                return None
            
            return GoogleCalendarIntegration(client_id, client_secret, redirect_uri)
        
        return None
