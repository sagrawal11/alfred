"""
Reminder Service
Handles reminder follow-ups and task decay checks
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo
from supabase import Client

from config import Config
from communication_service import CommunicationService
from data import TodoRepository, UserRepository, UserPreferencesRepository

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders and task decay"""
    
    def __init__(self, supabase: Client, config: Config, communication_service: CommunicationService):
        self.supabase = supabase
        self.config = config
        self.communication_service = communication_service
        self.todo_repo = TodoRepository(supabase)
        self.user_repo = UserRepository(supabase)
        self.user_prefs_repo = UserPreferencesRepository(supabase)
        
        # Store pending reschedules and task decay responses
        self.pending_reschedules: Dict[int, List[Dict[str, Any]]] = {}
        self.pending_task_decay: Dict[str, Dict[int, str]] = {}

    def _reminder_followup_message(self, content: str, style_bucket: str, reschedule_options: Optional[List[Dict[str, Any]]] = None) -> str:
        """Build reminder follow-up copy based on reminder_style_bucket (chill / moderate / formal)."""
        if reschedule_options:
            if style_bucket in ("relaxed", "minimal"):
                msg = f"Hey — did you get to {content}, or want to move it?\n"
            elif style_bucket in ("very_persistent", "persistent"):
                msg = f"Reminder: Did you get a chance to {content}, or should I reschedule it?\n"
            else:
                msg = f"Did you get a chance to {content}, or should I reschedule it?\n"
            msg += "Reply:\n• 'yes' or 'done' if completed\n"
            for i, opt in enumerate(reschedule_options, 1):
                msg += f"• '{i}' to reschedule to {opt.get('text', '')}\n"
            msg += "• 'no' to skip"
            return msg
        if style_bucket in ("relaxed", "minimal"):
            return f"Quick check — did you get to {content}? Reply 'yes' if done, or 'no' to skip."
        if style_bucket in ("very_persistent", "persistent"):
            return f"Reminder: Please confirm if you've completed: {content}. Reply 'yes' if done, or 'no' to skip."
        return f"Did you get a chance to {content}? Reply 'yes' if done, or 'no' to skip."

    def _task_decay_message(self, content: str, style_bucket: str) -> str:
        """Build task decay copy based on reminder_style_bucket."""
        if style_bucket in ("relaxed", "minimal"):
            return f"Still want '{content}' on your list? Reply 'keep', 'reschedule', or 'delete'."
        if style_bucket in ("very_persistent", "persistent"):
            return f"Reminder: Still want '{content}' on your list?\nReply:\n• 'keep' to keep it\n• 'reschedule' to move it\n• 'delete' or 'remove' to remove it"
        return f"Still want '{content}' on your list?\nReply:\n• 'keep' to keep it\n• 'reschedule' to move it\n• 'delete' or 'remove' to remove it"

    def check_reminder_followups(self):
        """Check for reminders that need follow-ups"""
        try:
            if not self.config.REMINDER_FOLLOWUP_DELAY_MINUTES:
                return
            
            current_time = datetime.now()
            followup_delay = timedelta(minutes=self.config.REMINDER_FOLLOWUP_DELAY_MINUTES)
            
            # Get all reminders that were sent but not completed
            # Query directly from database for all users
            result = self.supabase.table('reminders_todos')\
                .select("*")\
                .eq('type', 'reminder')\
                .eq('completed', False)\
                .not_.is_('sent_at', 'null')\
                .eq('follow_up_sent', False)\
                .execute()
            reminders = result.data if result.data else []
            
            for reminder in reminders:
                try:
                    reminder_id = reminder.get('id')
                    content = reminder.get('content', '')
                    sent_at_str = reminder.get('sent_at')
                    follow_up_sent = reminder.get('follow_up_sent', False)
                    user_id = reminder.get('user_id')
                    
                    # Skip if follow-up already sent
                    if follow_up_sent:
                        continue
                    
                    if not sent_at_str:
                        continue
                    
                    # Get user phone number and reminder style
                    user = self.user_repo.get_by_id(user_id)
                    if not user or not user.get('phone_number'):
                        continue
                    
                    user_phone = user['phone_number']
                    reminder_style = (user.get('reminder_style_bucket') or 'moderate').strip().lower()

                    # Respect quiet hours / do-not-disturb (best effort)
                    try:
                        prefs = self.user_prefs_repo.get(user_id) or {}
                        tz_name = (user.get('timezone') or 'UTC').strip() or 'UTC'
                        try:
                            user_tz = ZoneInfo(tz_name)
                        except Exception:
                            user_tz = ZoneInfo('UTC')
                        now_utc = datetime.now(tz=ZoneInfo('UTC'))
                        if prefs.get('do_not_disturb'):
                            continue
                        qs = prefs.get('quiet_hours_start')
                        qe = prefs.get('quiet_hours_end')
                        if qs is not None and qe is not None:
                            qs = int(qs); qe = int(qe)
                            local_hour = now_utc.astimezone(user_tz).hour
                            in_quiet = (qs < qe and qs <= local_hour < qe) or (qs > qe and (local_hour >= qs or local_hour < qe))
                            if in_quiet:
                                continue
                    except Exception:
                        pass
                    
                    # Parse sent_at timestamp
                    try:
                        sent_at = datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                        if sent_at.tzinfo is None:
                            sent_at = sent_at.replace(tzinfo=timezone.utc)
                    except:
                        # Try without timezone
                        sent_at = datetime.fromisoformat(sent_at_str)
                        sent_at = sent_at.replace(tzinfo=timezone.utc)
                    
                    # Make current_time timezone-aware for comparison
                    if current_time.tzinfo is None:
                        current_time_aware = current_time.replace(tzinfo=timezone.utc)
                    else:
                        current_time_aware = current_time
                    
                    time_since_sent = current_time_aware - sent_at
                    
                    # If enough time has passed, send follow-up
                    if time_since_sent >= followup_delay:
                        # Check if we should suggest rescheduling
                        due_date_str = reminder.get('due_date', '')
                        should_reschedule = False
                        reschedule_options = []
                        
                        if due_date_str and self.config.REMINDER_AUTO_RESCHEDULE_ENABLED:
                            try:
                                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                if due_date.tzinfo is None:
                                    due_date = due_date.replace(tzinfo=timezone.utc)
                                
                                if current_time.tzinfo is None:
                                    current_time_aware = current_time.replace(tzinfo=timezone.utc)
                                else:
                                    current_time_aware = current_time
                                
                                if due_date < current_time_aware:
                                    should_reschedule = True
                                    # Generate reschedule options
                                    tomorrow_morning = (current_time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                                    later_today = current_time + timedelta(hours=2)
                                    
                                    if later_today.hour < 20:  # Only suggest if before 8pm
                                        reschedule_options.append({
                                            'time': later_today,
                                            'text': f"later today ({later_today.strftime('%I:%M %p')})"
                                        })
                                    
                                    reschedule_options.append({
                                        'time': tomorrow_morning,
                                        'text': f"tomorrow morning ({tomorrow_morning.strftime('%I:%M %p')})"
                                    })
                            except Exception as e:
                                logger.debug(f"Error parsing due_date for reschedule: {e}")
                        
                        # Build follow-up message (tone from reminder_style_bucket)
                        if should_reschedule and reschedule_options:
                            message = self._reminder_followup_message(content, reminder_style, reschedule_options=reschedule_options[:3])
                            # Store reschedule options
                            self.pending_reschedules[reminder_id] = reschedule_options
                        else:
                            message = self._reminder_followup_message(content, reminder_style)
                        
                        # Send follow-up
                        result = self.communication_service.send_response(message, user_phone)
                        
                        if result['success']:
                            logger.info(f"Follow-up sent for reminder {reminder_id}: {content}")
                            # Mark follow-up as sent
                            self.todo_repo.update(reminder_id, {'follow_up_sent': True})
                        else:
                            logger.error(f"Failed to send follow-up: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    logger.error(f"Error processing follow-up for reminder {reminder_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking reminder follow-ups: {e}")
    
    def check_task_decay(self):
        """Check for stale todos and ask if they're still relevant"""
        try:
            if not self.config.TASK_DECAY_ENABLED:
                return
            
            current_time = datetime.now()
            decay_threshold = timedelta(days=self.config.TASK_DECAY_DAYS)
            
            # Get all incomplete todos that haven't had decay check sent
            result = self.supabase.table('reminders_todos')\
                .select("*")\
                .eq('type', 'todo')\
                .eq('completed', False)\
                .eq('decay_check_sent', False)\
                .execute()
            todos = result.data if result.data else []
            
            for todo in todos:
                try:
                    todo_id = todo.get('id')
                    content = todo.get('content', '')
                    timestamp_str = todo.get('created_at') or todo.get('timestamp', '')
                    decay_check_sent = todo.get('decay_check_sent', False)
                    user_id = todo.get('user_id')
                    
                    # Skip if decay check already sent
                    if decay_check_sent:
                        continue
                    
                    if not timestamp_str:
                        continue
                    
                    # Get user phone number and reminder style
                    user = self.user_repo.get_by_id(user_id)
                    if not user or not user.get('phone_number'):
                        continue
                    
                    user_phone = user['phone_number']
                    reminder_style = (user.get('reminder_style_bucket') or 'moderate').strip().lower()
                    
                    # Parse created_at timestamp
                    try:
                        created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                    except:
                        created_at = datetime.fromisoformat(timestamp_str)
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    # Make current_time timezone-aware for comparison
                    if current_time.tzinfo is None:
                        current_time_aware = current_time.replace(tzinfo=timezone.utc)
                    else:
                        current_time_aware = current_time
                    
                    age = current_time_aware - created_at
                    
                    # If task is older than threshold, send decay check (tone from reminder_style_bucket)
                    if age >= decay_threshold:
                        message = self._task_decay_message(content, reminder_style)
                        result = self.communication_service.send_response(message, user_phone)
                        
                        if result['success']:
                            logger.info(f"Task decay check sent for: {content}")
                            # Mark decay check as sent
                            self.todo_repo.update(todo_id, {'decay_check_sent': True})
                            
                            # Store pending response
                            if user_phone not in self.pending_task_decay:
                                self.pending_task_decay[user_phone] = {}
                            self.pending_task_decay[user_phone][todo_id] = content
                        else:
                            logger.error(f"Failed to send task decay check: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    logger.error(f"Error processing task decay for todo {todo_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking task decay: {e}")
