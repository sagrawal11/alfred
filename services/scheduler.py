"""
Background Job Scheduler
Manages all scheduled tasks using APScheduler
"""

import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from config import Config

logger = logging.getLogger(__name__)

# Suppress APScheduler "missed job" warnings on startup (normal when app restarts)
logging.getLogger('apscheduler.executors.default').setLevel(logging.ERROR)


class JobScheduler:
    """Manages background job scheduling"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler: Optional[BackgroundScheduler] = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the scheduler"""
        if self._initialized:
            return
        
        # Configure executor
        executors = {
            'default': ThreadPoolExecutor(max_workers=5)
        }
        
        # Configure job defaults
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 3600  # 1 hour grace period (suppresses warnings on restart)
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        self._initialized = True
        logger.info("Job scheduler initialized")
    
    def start(self):
        """Start the scheduler"""
        if not self._initialized:
            self.initialize()
        
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Job scheduler started")
    
    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Job scheduler shut down")
    
    def add_job(self, func, trigger, id: Optional[str] = None, **kwargs):
        """Add a job to the scheduler"""
        if not self._initialized:
            self.initialize()
        
        if not self.scheduler.running:
            self.start()
        
        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=id,
            replace_existing=True,  # Replace if job with same ID exists
            **kwargs
        )
        logger.info(f"Job added: {id or func.__name__}")
    
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler"""
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Job removed: {job_id}")
            except Exception as e:
                logger.warning(f"Failed to remove job {job_id}: {e}")
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        if self.scheduler:
            return self.scheduler.get_jobs()
        return []
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler is not None and self.scheduler.running
