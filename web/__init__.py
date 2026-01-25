"""
Web Module
Dashboard and authentication components
"""

from .auth import AuthManager
from .routes import register_web_routes
from .dashboard import DashboardData

__all__ = ['AuthManager', 'register_web_routes', 'DashboardData']
