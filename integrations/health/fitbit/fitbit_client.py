"""
Fitbit Integration
Handles Fitbit OAuth and data syncing
"""

import os
import base64
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from integrations.base import BaseIntegration, SyncResult, SyncStatus


class FitbitIntegration(BaseIntegration):
    """Fitbit integration"""
    
    FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
    FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
    FITBIT_API_BASE = "https://api.fitbit.com/1/user/-"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__('fitbit', client_id, client_secret, redirect_uri)
    
    def get_authorization_url(self, state: str, scopes: List[str]) -> str:
        """Generate Fitbit OAuth authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'state': state
        }
        return f"{self.FITBIT_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        # Fitbit requires Basic Auth with client_id:client_secret
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        response = requests.post(self.FITBIT_TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': tokens.get('expires_in', 28800),  # Default 8 hours
            'user_id': tokens.get('user_id'),
            'scope': tokens.get('scope', '')
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Fitbit access token"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        response = requests.post(self.FITBIT_TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens.get('refresh_token', refresh_token),  # May or may not rotate
            'expires_in': tokens.get('expires_in', 28800)
        }
    
    def sync_data(self, access_token: str, user_id: int,
                 last_sync_at: Optional[datetime] = None) -> SyncResult:
        """Sync Fitbit data (activities and sleep)"""
        headers = {'Authorization': f'Bearer {access_token}'}
        synced_items = []
        items_synced = 0
        items_failed = 0
        
        try:
            # Sync activities (workouts)
            activities = self._fetch_activities(headers, last_sync_at)
            for activity in activities:
                try:
                    mapped = self.map_external_to_internal(activity)
                    synced_items.append({
                        'external_id': activity.get('logId'),
                        'internal_type': 'gym_log',
                        'internal_data': mapped,
                        'external_data': activity
                    })
                    items_synced += 1
                except Exception as e:
                    print(f"Error mapping Fitbit activity: {e}")
                    items_failed += 1
            
            # Sync sleep logs
            sleep_logs = self._fetch_sleep_logs(headers, last_sync_at)
            for sleep in sleep_logs:
                try:
                    mapped = self.map_sleep_to_internal(sleep)
                    synced_items.append({
                        'external_id': sleep.get('logId'),
                        'internal_type': 'sleep_log',
                        'internal_data': mapped,
                        'external_data': sleep
                    })
                    items_synced += 1
                except Exception as e:
                    print(f"Error mapping Fitbit sleep: {e}")
                    items_failed += 1
            
            status = SyncStatus.SUCCESS if items_failed == 0 else SyncStatus.PARTIAL
            return SyncResult(status, items_synced, items_failed, data=synced_items)
            
        except Exception as e:
            return SyncResult(SyncStatus.ERROR, items_synced, items_failed, 
                            error_message=str(e))
    
    def _fetch_activities(self, headers: Dict, last_sync_at: Optional[datetime]) -> List[Dict]:
        """Fetch Fitbit activities"""
        # Fetch last 30 days or since last sync
        end_date = datetime.now().date()
        if last_sync_at:
            start_date = last_sync_at.date()
        else:
            start_date = end_date - timedelta(days=30)
        
        activities = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"{self.FITBIT_API_BASE}/activities/date/{date_str}.json"
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Extract activities from summary
                if 'summary' in data and 'activities' in data['summary']:
                    for activity in data['summary']['activities']:
                        if activity.get('activityName') and activity.get('duration'):
                            activities.append({
                                'logId': f"{date_str}-{activity.get('activityName')}",
                                'activityName': activity['activityName'],
                                'duration': activity.get('duration', 0),
                                'calories': activity.get('calories', 0),
                                'date': date_str
                            })
            except Exception as e:
                print(f"Error fetching Fitbit activities for {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        return activities
    
    def _fetch_sleep_logs(self, headers: Dict, last_sync_at: Optional[datetime]) -> List[Dict]:
        """Fetch Fitbit sleep logs"""
        end_date = datetime.now().date()
        if last_sync_at:
            start_date = last_sync_at.date()
        else:
            start_date = end_date - timedelta(days=30)
        
        url = f"{self.FITBIT_API_BASE}/sleep/date/{start_date}/{end_date}.json"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            sleep_logs = []
            for sleep in data.get('sleep', []):
                sleep_logs.append({
                    'logId': str(sleep.get('logId')),
                    'dateOfSleep': sleep.get('dateOfSleep'),
                    'startTime': sleep.get('startTime'),
                    'endTime': sleep.get('endTime'),
                    'duration': sleep.get('duration', 0),  # in milliseconds
                    'minutesAsleep': sleep.get('minutesAsleep', 0)
                })
            
            return sleep_logs
        except Exception as e:
            print(f"Error fetching Fitbit sleep logs: {e}")
            return []
    
    def map_external_to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Fitbit activity to internal gym_log format"""
        activity_name = external_data.get('activityName', 'Unknown')
        duration_seconds = external_data.get('duration', 0)
        duration_minutes = duration_seconds / 60 if duration_seconds else 0
        calories = external_data.get('calories', 0)
        
        return {
            'exercise': activity_name,
            'sets': 1,  # Fitbit doesn't provide sets/reps
            'reps': None,
            'weight': None,
            'notes': f"Synced from Fitbit: {duration_minutes:.0f} min, {calories} cal"
        }
    
    def map_sleep_to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Fitbit sleep to internal sleep_log format"""
        date_str = external_data.get('dateOfSleep', '')
        duration_ms = external_data.get('duration', 0)
        duration_hours = duration_ms / (1000 * 60 * 60) if duration_ms else 0
        
        # Parse start and end times
        start_time_str = external_data.get('startTime', '')
        end_time_str = external_data.get('endTime', '')
        
        # Fitbit returns times like "2024-01-15T22:30:00.000"
        try:
            if start_time_str:
                start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                start_time = start_dt.time()
            else:
                start_time = None
            
            if end_time_str:
                end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                end_time = end_dt.time()
            else:
                end_time = None
        except Exception:
            start_time = None
            end_time = None
        
        return {
            'date': date_str,
            'sleep_time': start_time.isoformat() if start_time else None,
            'wake_time': end_time.isoformat() if end_time else None,
            'duration_hours': round(duration_hours, 2)
        }
