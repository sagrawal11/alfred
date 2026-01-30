"""
Services Package
Background job services for scheduled tasks
"""

"""
Note: keep imports lightweight.
Some environments (tests/CI) may import subpackages (e.g. `services.nutrition`)
without having optional runtime deps available.
"""

try:
    from .scheduler import JobScheduler
    from .reminder_service import ReminderService
    from .sync_service import SyncService
    from .notification_service import NotificationService
except Exception:  # pragma: no cover
    JobScheduler = None  # type: ignore[assignment]
    ReminderService = None  # type: ignore[assignment]
    SyncService = None  # type: ignore[assignment]
    NotificationService = None  # type: ignore[assignment]

__all__ = [
    'JobScheduler',
    'ReminderService',
    'SyncService',
    'NotificationService'
]
