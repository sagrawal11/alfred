"""
Communication Service for Alfred the Butler
Handles SMS via Twilio REST API (for scheduled messages)
Note: Incoming SMS responses use TwiML (handled in app.py webhook)
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

class CommunicationService:
    """Handles all communication methods for Alfred the Butler"""
    
    def __init__(self):
        self.config = Config()
        self.mode = self.config.COMMUNICATION_MODE
        
        # Initialize Twilio client for scheduled/outbound messages
        self.twilio_client = None
        if self.mode == 'sms':
            self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client for REST API (used for scheduled messages)"""
        try:
            from twilio.rest import Client as twilio_client
            
            if not self.config.TWILIO_ACCOUNT_SID or not self.config.TWILIO_AUTH_TOKEN:
                print("⚠️  Twilio credentials not configured. Scheduled SMS functionality disabled.")
                self.twilio_client = None
                return
            
            self.twilio_client = twilio_client(
                self.config.TWILIO_ACCOUNT_SID,
                self.config.TWILIO_AUTH_TOKEN
            )
            print("✅ Twilio REST client initialized successfully (for scheduled messages)")
            
        except ImportError:
            print("⚠️  Twilio package not installed. Scheduled SMS functionality disabled.")
            self.twilio_client = None
        except Exception as e:
            print(f"❌ Failed to initialize Twilio: {e}")
            self.twilio_client = None
    
    def send_response(self, message: str, phone_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Send SMS via Twilio REST API
        
        Args:
            message: The message to send
            phone_number: Phone number to send SMS to
        
        Returns:
            Dict with status and details
        """
        if self.mode == 'sms':
            return self._send_sms(message, phone_number)
        else:
            raise ValueError(f"Invalid communication mode: {self.mode}. Only 'sms' is supported.")
    
    def _send_sms(self, message: str, phone_number: str) -> Dict[str, Any]:
        """Send SMS via Twilio REST API (for scheduled/outbound messages)"""
        if not self.twilio_client:
            return {
                'success': False,
                'method': 'sms',
                'error': 'Twilio client not initialized',
                'timestamp': datetime.now().isoformat()
            }
        
        if not phone_number:
            return {
                'success': False,
                'method': 'sms',
                'error': 'No phone number provided',
                'timestamp': datetime.now().isoformat()
            }
        
        if not self.config.TWILIO_PHONE_NUMBER:
            return {
                'success': False,
                'method': 'sms',
                'error': 'Twilio phone number not configured',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Send SMS via Twilio REST API
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=self.config.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            print(f"📱 SMS sent via Twilio REST API: {message_obj.sid}")
            
            return {
                'success': True,
                'method': 'sms',
                'message_id': message_obj.sid,
                'timestamp': datetime.now().isoformat(),
                'to': phone_number,
                'from': self.config.TWILIO_PHONE_NUMBER
            }
            
        except Exception as e:
            print(f"❌ SMS failed: {e}")
            return {
                'success': False,
                'method': 'sms',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get communication service status"""
        return {
            'mode': self.mode,
            'twilio_available': self.twilio_client is not None,
            'timestamp': datetime.now().isoformat()
        }
