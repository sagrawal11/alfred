"""
Web Integration Routes
Routes for managing integrations via web dashboard
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from typing import Callable

from integrations import IntegrationAuthManager, SyncManager
from integrations.health.fitbit import FitbitIntegration
from integrations.calendar.google_calendar import GoogleCalendarIntegration
from data import IntegrationRepository
from web.auth import AuthManager


def register_integration_routes(app: Flask, supabase, auth_manager: AuthManager,
                                 integration_repo: IntegrationRepository,
                                 integration_auth: IntegrationAuthManager,
                                 sync_manager: SyncManager):
    """
    Register integration management routes
    
    Args:
        app: Flask application instance
        supabase: Supabase client
        auth_manager: AuthManager instance
        integration_repo: IntegrationRepository instance
        integration_auth: IntegrationAuthManager instance
        sync_manager: SyncManager instance
    """
    
    def require_login(f: Callable) -> Callable:
        """Decorator to require login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = auth_manager.require_auth()
            if not user:
                return redirect(url_for('dashboard_login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # ============================================================================
    # Integration Management Routes
    # ============================================================================
    
    @app.route('/dashboard/integrations')
    @require_login
    def dashboard_integrations():
        """Integration management page"""
        user = auth_manager.get_current_user()
        connections = integration_repo.get_user_connections(user['id'])
        
        # Group by provider
        connections_by_provider = {}
        for conn in connections:
            provider = conn['provider']
            if provider not in connections_by_provider:
                connections_by_provider[provider] = []
            connections_by_provider[provider].append(conn)
        
        return render_template('dashboard/integrations.html', 
                             connections=connections_by_provider)
    
    @app.route('/dashboard/integrations/<provider>/connect')
    @require_login
    def dashboard_integration_connect(provider: str):
        """Initiate OAuth flow for an integration"""
        user = auth_manager.get_current_user()
        
        # Get integration instance based on provider
        integration = _get_integration_instance(provider)
        if not integration:
            flash(f'Integration {provider} not available', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        # Get required scopes for provider
        scopes = _get_provider_scopes(provider)
        
        # Initiate OAuth
        auth_url, state = integration_auth.initiate_oauth(
            user_id=user['id'],
            provider=provider,
            integration=integration,
            scopes=scopes
        )
        
        # Store state in session for verification
        session[f'oauth_state_{provider}'] = state
        
        return redirect(auth_url)
    
    @app.route('/dashboard/integrations/<provider>/callback')
    @require_login
    def dashboard_integration_callback(provider: str):
        """Handle OAuth callback"""
        user = auth_manager.get_current_user()
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            flash(f'OAuth error: {error}', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        if not code:
            flash('No authorization code received', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        # Verify state
        stored_state = session.get(f'oauth_state_{provider}')
        if not stored_state or stored_state != state:
            flash('Invalid state token', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        # Get integration instance
        integration = _get_integration_instance(provider)
        if not integration:
            flash(f'Integration {provider} not available', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        # Complete OAuth
        success, error_msg, connection = integration_auth.complete_oauth(
            user_id=user['id'],
            provider=provider,
            integration=integration,
            code=code,
            state=state
        )
        
        if success:
            # Perform initial sync
            try:
                sync_result = sync_manager.sync_integration(
                    connection_id=connection['id'],
                    integration=integration,
                    sync_type='full'
                )
                
                if sync_result.status.value == 'success':
                    flash(f'{provider.title()} connected! Synced {sync_result.items_synced} items.', 'success')
                else:
                    flash(f'{provider.title()} connected, but sync had issues: {sync_result.error_message}', 'warning')
            except Exception as e:
                flash(f'{provider.title()} connected, but initial sync failed: {str(e)}', 'warning')
        else:
            flash(f'Connection failed: {error_msg}', 'error')
        
        # Clear state
        session.pop(f'oauth_state_{provider}', None)
        
        return redirect(url_for('dashboard_integrations'))
    
    @app.route('/dashboard/integrations/<int:connection_id>/disconnect', methods=['POST'])
    @require_login
    def dashboard_integration_disconnect(connection_id: int):
        """Disconnect an integration"""
        user = auth_manager.get_current_user()
        
        # Verify connection belongs to user
        connection = integration_repo.get_by_id(connection_id)
        if not connection or connection['user_id'] != user['id']:
            flash('Connection not found', 'error')
            return redirect(url_for('dashboard_integrations'))
        
        # Deactivate connection
        integration_repo.deactivate_connection(connection_id)
        flash('Integration disconnected', 'success')
        
        return redirect(url_for('dashboard_integrations'))
    
    @app.route('/dashboard/integrations/<int:connection_id>/sync', methods=['POST'])
    @require_login
    def dashboard_integration_sync(connection_id: int):
        """Manually trigger sync for an integration"""
        user = auth_manager.get_current_user()
        
        # Verify connection belongs to user
        connection = integration_repo.get_by_id(connection_id)
        if not connection or connection['user_id'] != user['id']:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Get integration instance
        integration = _get_integration_instance(connection['provider'])
        if not integration:
            return jsonify({'error': 'Integration not available'}), 400
        
        # Perform sync
        sync_result = sync_manager.sync_integration(
            connection_id=connection_id,
            integration=integration,
            sync_type='full'
        )
        
        return jsonify({
            'status': sync_result.status.value,
            'items_synced': sync_result.items_synced,
            'items_failed': sync_result.items_failed,
            'error': sync_result.error_message
        })
    
    # ============================================================================
    # Helper Functions
    # ============================================================================
    
    def _get_integration_instance(provider: str):
        """Get integration instance for a provider"""
        import os
        
        if provider == 'fitbit':
            client_id = os.getenv('FITBIT_CLIENT_ID')
            client_secret = os.getenv('FITBIT_CLIENT_SECRET')
            redirect_uri = f"{request.host_url.rstrip('/')}/dashboard/integrations/fitbit/callback"
            
            if not client_id or not client_secret:
                return None
            
            return FitbitIntegration(client_id, client_secret, redirect_uri)
        
        elif provider == 'google_calendar':
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            redirect_uri = f"{request.host_url.rstrip('/')}/dashboard/integrations/google_calendar/callback"
            
            if not client_id or not client_secret:
                return None
            
            return GoogleCalendarIntegration(client_id, client_secret, redirect_uri)
        
        # Add more providers as needed
        return None
    
    def _get_provider_scopes(provider: str) -> list:
        """Get required OAuth scopes for a provider"""
        scope_map = {
            'fitbit': ['activity', 'sleep', 'heartrate'],
            'google_calendar': ['https://www.googleapis.com/auth/calendar.events.readonly'],
            'google_fit': ['https://www.googleapis.com/auth/fitness.activity.read']
        }
        return scope_map.get(provider, [])
