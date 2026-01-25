"""
Integrations Module
Third-party integration system (Fitbit, Google Calendar, Google Fit, etc.)
"""

from .base import BaseIntegration, IntegrationResult, SyncResult, SyncStatus
from .auth import IntegrationAuthManager
from .sync_manager import SyncManager
from .webhooks import WebhookHandler

__all__ = [
    'BaseIntegration',
    'IntegrationResult',
    'SyncResult',
    'SyncStatus',
    'IntegrationAuthManager',
    'SyncManager',
    'WebhookHandler',
]
