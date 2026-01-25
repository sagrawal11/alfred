"""
Webhook Handlers
Handle real-time updates from integration providers
"""

from typing import Dict, Optional
from flask import Request
from datetime import datetime

from data import IntegrationRepository
from integrations import SyncManager
from integrations.health.fitbit import FitbitIntegration
import os


class WebhookHandler:
    """Handles webhooks from integration providers"""
    
    def __init__(self, integration_repo: IntegrationRepository,
                 sync_manager: SyncManager):
        """
        Initialize webhook handler
        
        Args:
            integration_repo: IntegrationRepository instance
            sync_manager: SyncManager instance
        """
        self.integration_repo = integration_repo
        self.sync_manager = sync_manager
    
    def handle_fitbit_webhook(self, request: Request) -> Dict:
        """
        Handle Fitbit webhook
        
        Args:
            request: Flask request object
            
        Returns:
            Response dictionary
        """
        # Fitbit webhook verification
        if request.method == 'GET':
            # Fitbit sends GET request for verification
            verify = request.args.get('verify')
            if verify:
                # Return verification code
                return {'verify': verify}
        
        # Process webhook data
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Extract user ID from webhook data
            # Fitbit webhooks include user ID
            user_id_str = data.get('ownerId') or data.get('userId')
            if not user_id_str:
                return {'error': 'No user ID in webhook'}, 400
            
            # Find connection by provider user ID
            # Note: This requires storing provider_user_id in connections
            connection = self._find_connection_by_provider_user_id('fitbit', user_id_str)
            if not connection:
                return {'error': 'Connection not found'}, 404
            
            # Get integration instance
            integration = self._get_fitbit_integration()
            if not integration:
                return {'error': 'Fitbit integration not configured'}, 500
            
            # Trigger sync
            sync_result = self.sync_manager.sync_integration(
                connection_id=connection['id'],
                integration=integration,
                sync_type='webhook'
            )
            
            return {
                'status': 'success',
                'items_synced': sync_result.items_synced
            }
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    def handle_google_webhook(self, request: Request, provider: str) -> Dict:
        """
        Handle Google webhook (Calendar, Fit, etc.)
        
        Args:
            request: Flask request object
            provider: Provider name ('google_calendar', 'google_fit')
            
        Returns:
            Response dictionary
        """
        # Google uses Pub/Sub for webhooks, which is more complex
        # For now, return basic handler
        try:
            data = request.get_json()
            
            # Google Pub/Sub webhook structure
            # This is a simplified handler - full implementation would parse Pub/Sub messages
            
            return {'status': 'received'}
        except Exception as e:
            return {'error': str(e)}, 500
    
    def _find_connection_by_provider_user_id(self, provider: str, provider_user_id: str) -> Optional[Dict]:
        """Find connection by provider user ID"""
        result = self.integration_repo.client.table('user_integrations')\
            .select("*")\
            .eq("provider", provider)\
            .eq("provider_user_id", provider_user_id)\
            .eq("is_active", True)\
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def _get_fitbit_integration(self) -> Optional[FitbitIntegration]:
        """Get Fitbit integration instance"""
        client_id = os.getenv('FITBIT_CLIENT_ID')
        client_secret = os.getenv('FITBIT_CLIENT_SECRET')
        redirect_uri = os.getenv('BASE_URL', 'http://localhost:5001') + "/dashboard/integrations/fitbit/callback"
        
        if not client_id or not client_secret:
            return None
        
        return FitbitIntegration(client_id, client_secret, redirect_uri)
