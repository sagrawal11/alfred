#!/usr/bin/env python3
"""
Google Calendar API Integration
Handles fetching calendar events using OAuth 2.0
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

# Calendar API scope (read-only)
# Using calendar.events.owned.readonly - allows reading events you own
SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned.readonly']


class GoogleCalendarService:
    """Service for interacting with Google Calendar API"""
    
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, redirect_uri: str):
        """Initialize Google Calendar service
        
        Args:
            client_id: OAuth 2.0 Client ID
            client_secret: OAuth 2.0 Client Secret
            refresh_token: OAuth 2.0 Refresh Token
            redirect_uri: OAuth 2.0 Redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.redirect_uri = redirect_uri
        self.service = None
        self._credentials = None
    
    def _get_credentials(self) -> Credentials:
        """Get valid user credentials, refreshing if necessary"""
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        # Create credentials from refresh token
        self._credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=SCOPES
        )
        
        # Refresh the access token
        try:
            self._credentials.refresh(Request())
        except Exception as e:
            print(f" Error refreshing Google Calendar credentials: {e}")
            raise
        
        return self._credentials
    
    def _get_service(self):
        """Get Google Calendar service instance"""
        if self.service is None:
            try:
                credentials = self._get_credentials()
                self.service = build('calendar', 'v3', credentials=credentials)
            except Exception as e:
                print(f" Error building Google Calendar service: {e}")
                raise
        return self.service
    
    def get_todays_events(self) -> List[Dict]:
        """Get all events for today
        
        Returns:
            List of event dictionaries with 'summary', 'start', 'end', etc.
        """
        try:
            service = self._get_service()
            today = datetime.now().date()
            time_min = datetime.combine(today, datetime.min.time()).isoformat() + 'Z'
            time_max = datetime.combine(today, datetime.max.time()).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            print(f" Error fetching today's calendar events: {error}")
            return []
        except Exception as e:
            print(f" Unexpected error fetching calendar events: {e}")
            return []
    
    def get_events_for_date(self, target_date: datetime.date) -> List[Dict]:
        """Get all events for a specific date
        
        Args:
            target_date: Date to get events for
            
        Returns:
            List of event dictionaries
        """
        try:
            service = self._get_service()
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
            
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            print(f" Error fetching calendar events for {target_date}: {error}")
            return []
        except Exception as e:
            print(f" Unexpected error fetching calendar events: {e}")
            return []
    
    def format_event_for_display(self, event: Dict) -> str:
        """Format a calendar event for SMS display
        
        Args:
            event: Event dictionary from Google Calendar API
            
        Returns:
            Formatted string like "3:00 PM - Meeting with team"
        """
        summary = event.get('summary', 'No title')
        start = event.get('start', {})
        
        # Parse start time
        if 'dateTime' in start:
            # Has specific time
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            time_str = start_time.strftime("%I:%M %p")
            return f"{time_str} - {summary}"
        elif 'date' in start:
            # All-day event
            return f"All day - {summary}"
        else:
            return summary
    
    def get_todays_events_formatted(self) -> List[str]:
        """Get today's events formatted for display
        
        Returns:
            List of formatted event strings
        """
        events = self.get_todays_events()
        formatted = []
        
        for event in events:
            formatted.append(self.format_event_for_display(event))
        
        return formatted


def create_calendar_service(config) -> Optional[GoogleCalendarService]:
    """Create a Google Calendar service instance from config
    
    Args:
        config: Config object with Google Calendar credentials
        
    Returns:
        GoogleCalendarService instance or None if credentials are missing
    """
    if not all([
        config.GOOGLE_CLIENT_ID,
        config.GOOGLE_CLIENT_SECRET,
        config.GOOGLE_REFRESH_TOKEN,
        config.GOOGLE_REDIRECT_URI
    ]):
        print("  Google Calendar credentials not configured, skipping calendar integration")
        return None
    
    try:
        return GoogleCalendarService(
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            refresh_token=config.GOOGLE_REFRESH_TOKEN,
            redirect_uri=config.GOOGLE_REDIRECT_URI
        )
    except Exception as e:
        print(f" Error creating Google Calendar service: {e}")
        return None

