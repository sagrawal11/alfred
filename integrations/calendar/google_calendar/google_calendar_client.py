"""
Google Calendar Integration
Handles Google Calendar OAuth and event syncing
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from integrations.base import BaseIntegration, SyncResult, SyncStatus


class GoogleCalendarIntegration(BaseIntegration):
    """Google Calendar integration"""
    
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPES = ['https://www.googleapis.com/auth/calendar.events.readonly']
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__('google_calendar', client_id, client_secret, redirect_uri)
    
    def get_authorization_url(self, state: str, scopes: List[str]) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'access_type': 'offline',  # Required for refresh token
            'prompt': 'consent',  # Force consent to get refresh token
            'state': state
        }
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens.get('refresh_token'),
            'expires_in': tokens.get('expires_in', 3600),
            'scope': tokens.get('scope', '')
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google access token"""
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=self.GOOGLE_TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        credentials.refresh(Request())
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token or refresh_token,
            'expires_in': 3600  # Google tokens typically last 1 hour
        }
    
    def sync_data(self, access_token: str, user_id: int,
                 last_sync_at: Optional[datetime] = None) -> SyncResult:
        """Sync Google Calendar events (for context, not storage)"""
        # Calendar events are used for context, not stored as logs
        # So we return empty sync result but could fetch events for context
        try:
            credentials = Credentials(token=access_token)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Fetch events (for context in queries)
            time_min = datetime.now().isoformat() + 'Z'
            time_max = (datetime.now() + timedelta(days=7)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calendar events are not stored, just returned for context
            return SyncResult(
                SyncStatus.SUCCESS,
                items_synced=len(events),
                data=[{'type': 'calendar_event', 'data': event} for event in events]
            )
            
        except HttpError as e:
            return SyncResult(SyncStatus.ERROR, error_message=f"Google Calendar API error: {str(e)}")
        except Exception as e:
            return SyncResult(SyncStatus.ERROR, error_message=str(e))
    
    def map_external_to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Google Calendar event to internal format (for context)"""
        # Calendar events are used for context, not stored
        return {
            'type': 'calendar_event',
            'summary': external_data.get('summary', ''),
            'start': external_data.get('start', {}),
            'end': external_data.get('end', {}),
            'description': external_data.get('description', '')
        }
    
    def get_events_for_date(self, access_token: str, target_date: datetime.date) -> List[Dict]:
        """Get calendar events for a specific date"""
        try:
            credentials = Credentials(token=access_token)
            service = build('calendar', 'v3', credentials=credentials)
            
            time_min = datetime.combine(target_date, datetime.min.time()).isoformat() + 'Z'
            time_max = datetime.combine(target_date, datetime.max.time()).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except Exception as e:
            print(f"Error fetching Google Calendar events: {e}")
            return []
