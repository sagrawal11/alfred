"""
Notification Service
Handles gentle nudges and weekly digests
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo
from supabase import Client

from config import Config
from communication_service import CommunicationService
from data import (
    UserRepository,
    UserPreferencesRepository,
    WaterRepository,
    GymRepository,
    FoodRepository,
    TodoRepository,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications (nudges, digests)"""

    QUOTES = [
        ("Small steps, every day.", None),
        ("You don’t have to do it all. You just have to do the next thing.", None),
        ("Discipline is choosing what you want most over what you want now.", None),
        ("A little progress today beats a lot of perfection tomorrow.", None),
        ("Make it easy to do the right thing.", None),
    ]
    
    def __init__(self, supabase: Client, config: Config, communication_service: CommunicationService):
        self.supabase = supabase
        self.config = config
        self.communication_service = communication_service
        self.user_repo = UserRepository(supabase)
        self.user_prefs_repo = UserPreferencesRepository(supabase)
        self.water_repo = WaterRepository(supabase)
        self.gym_repo = GymRepository(supabase)
        self.food_repo = FoodRepository(supabase)
        self.todo_repo = TodoRepository(supabase)
        self._owm = None

    def _get_units(self, prefs: Dict[str, Any]) -> str:
        u = (prefs or {}).get("units")
        return u if u in ("metric", "imperial") else "metric"

    def _format_water_amount(self, ml: float, units: str) -> str:
        if units == "imperial":
            oz = ml / 29.5735
            return f"{oz:.0f}oz"
        if ml >= 1000:
            return f"{(ml / 1000.0):.1f}L"
        return f"{int(ml)}mL"

    def _format_water_progress(self, total_ml: float, goal_ml: Optional[int], units: str) -> str:
        if not goal_ml:
            return self._format_water_amount(total_ml, units)
        if units == "imperial":
            total_oz = total_ml / 29.5735
            goal_oz = float(goal_ml) / 29.5735
            return f"{total_oz:.0f}/{goal_oz:.0f}oz"
        total_l = total_ml / 1000.0
        goal_l = float(goal_ml) / 1000.0
        return f"{total_l:.1f}/{goal_l:.1f}L"

    def _get_water_goal_for_date(self, user_id: int, date_iso: str, prefs: Dict[str, Any]) -> Optional[int]:
        # per-day override
        try:
            wg = (
                self.supabase.table("water_goals")
                .select("goal_ml")
                .eq("user_id", user_id)
                .eq("date", date_iso)
                .limit(1)
                .execute()
            )
            if wg.data and wg.data[0].get("goal_ml") is not None:
                return int(float(wg.data[0]["goal_ml"]))
        except Exception:
            pass

        # default
        goal = (prefs or {}).get("default_water_goal_ml")
        try:
            return int(goal) if goal else None
        except Exception:
            return None

    def _get_weather_line(self, user: Dict[str, Any], prefs: Dict[str, Any]) -> Optional[str]:
        api_key = (self.config.WEATHER_API_KEY or "").strip()
        if not api_key:
            return None

        try:
            from pyowm import OWM
        except Exception:
            return None

        if self._owm is None:
            try:
                self._owm = OWM(api_key)
            except Exception:
                return None

        units = self._get_units(prefs)
        lat = user.get("location_lat")
        lon = user.get("location_lon")
        loc_name = user.get("location_name") or self.config.WEATHER_LOCATION

        try:
            mgr = self._owm.weather_manager()
            if lat is not None and lon is not None:
                obs = mgr.weather_at_coords(float(lat), float(lon))
            elif loc_name:
                obs = mgr.weather_at_place(str(loc_name))
            else:
                return None

            w = obs.weather
            status = (w.detailed_status or w.status or "").strip()
            temp_c = w.temperature("celsius")
            t = temp_c.get("temp")
            tmin = temp_c.get("temp_min")
            tmax = temp_c.get("temp_max")

            def c_to_f(x: Optional[float]) -> Optional[float]:
                if x is None:
                    return None
                return x * 9.0 / 5.0 + 32.0

            if units == "imperial":
                t = c_to_f(t)
                tmin = c_to_f(tmin)
                tmax = c_to_f(tmax)
                unit = "°F"
            else:
                unit = "°C"

            if t is None:
                return None

            line = f"Weather: {t:.0f}{unit}"
            if status:
                line += f", {status}"
            if tmax is not None and tmin is not None:
                line += f" (H {tmax:.0f} / L {tmin:.0f})"
            return line
        except Exception:
            return None

    def _get_user_tz(self, user: Dict[str, Any]) -> ZoneInfo:
        tz_name = (user.get("timezone") or "UTC").strip() or "UTC"
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("UTC")

    def _get_prefs(self, user_id: int) -> Dict[str, Any]:
        try:
            return self.user_prefs_repo.ensure(user_id)
        except Exception:
            return {}

    def _is_in_quiet_hours(self, prefs: Dict[str, Any], user_tz: ZoneInfo, now_utc: datetime) -> bool:
        if not prefs:
            return False
        if prefs.get("do_not_disturb"):
            return True

        start = prefs.get("quiet_hours_start")
        end = prefs.get("quiet_hours_end")
        if start is None or end is None:
            return False
        try:
            start = int(start)
            end = int(end)
        except Exception:
            return False

        local = now_utc.astimezone(user_tz)
        hour = local.hour
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    def _pick_daily_quote(self, user_id: int, today_iso: str) -> Optional[str]:
        """Return a quote string and record it in used_quotes (best-effort)."""
        try:
            existing = (
                self.supabase.table("used_quotes")
                .select("*")
                .eq("user_id", user_id)
                .eq("date", today_iso)
                .limit(1)
                .execute()
            )
            if existing.data:
                q = existing.data[0].get("quote")
                a = existing.data[0].get("author")
                if q:
                    return f"“{q}”" + (f" — {a}" if a else "")

            quote, author = self.QUOTES[int(datetime.now().timestamp()) % len(self.QUOTES)]
            self.supabase.table("used_quotes").insert(
                {"user_id": user_id, "date": today_iso, "quote": quote, "author": author}
            ).execute()
            return f"“{quote}”" + (f" — {author}" if author else "")
        except Exception:
            quote, author = self.QUOTES[int(datetime.now().timestamp()) % len(self.QUOTES)]
            return f"“{quote}”" + (f" — {author}" if author else "")
    
    def check_gentle_nudges(self):
        """Check and send gentle nudges for water and gym"""
        try:
            if not self.config.GENTLE_NUDGES_ENABLED:
                return
            
            current_time = datetime.now(tz=ZoneInfo("UTC"))
            
            # Get all users with phone numbers
            result = self.supabase.table('users')\
                .select("*")\
                .not_.is_('phone_number', 'null')\
                .execute()
            
            users = result.data if result.data else []
            
            for user in users:
                try:
                    user_id = user['id']
                    user_phone = user.get('phone_number')
                    
                    if not user_phone or user_phone.startswith('web-'):
                        continue  # Skip web-only users

                    prefs = self._get_prefs(user_id)
                    user_tz = self._get_user_tz(user)
                    if self._is_in_quiet_hours(prefs, user_tz, current_time):
                        continue
                    
                    # Check water intake
                    self._check_water_nudge(user_id, user_phone, current_time, user=user, prefs=prefs)
                    
                    # Check gym activity
                    self._check_gym_nudge(user_id, user_phone, current_time)
                
                except Exception as e:
                    logger.error(f"Error checking nudges for user {user_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking gentle nudges: {e}")
    
    def _check_water_nudge(self, user_id: int, user_phone: str, current_time: datetime, *, user: Dict[str, Any], prefs: Dict[str, Any]):
        """Check if user needs a water nudge"""
        try:
            # Get today's water intake
            today_str = current_time.date().isoformat()
            today_logs = self.water_repo.get_by_date(user_id, today_str)
            
            total_ml = sum(float(log.get('amount_ml', 0)) for log in today_logs)
            
            # Get goal (per-user default if set)
            goal_ml = prefs.get("default_water_goal_ml") if prefs else None
            try:
                goal_ml = int(goal_ml) if goal_ml else None
            except Exception:
                goal_ml = None
            if not goal_ml:
                goal_ml = self.config.DEFAULT_WATER_GOAL_ML
            
            # Calculate expected intake at this time of day
            hour = current_time.hour
            expected_progress = hour / 16.0  # Assume 16-hour day (8am to midnight)
            expected_ml = goal_ml * expected_progress
            
            # If significantly behind (more than 20% behind expected)
            if total_ml < expected_ml * 0.8 and expected_ml > 500:
                bottle_ml = user.get("water_bottle_ml") or self.config.WATER_BOTTLE_SIZE_ML
                try:
                    bottle_ml = int(bottle_ml)
                except Exception:
                    bottle_ml = self.config.WATER_BOTTLE_SIZE_ML
                bottles_behind = int((expected_ml - total_ml) / bottle_ml) if bottle_ml else 0
                message = f"You're about {bottles_behind} bottle{'s' if bottles_behind > 1 else ''} behind your usual pace today. Just a gentle reminder!"
                
                result = self.communication_service.send_response(message, user_phone)
                if result['success']:
                    logger.info(f"Water nudge sent to user {user_id}")
        
        except Exception as e:
            logger.debug(f"Error checking water nudge: {e}")
    
    def _check_gym_nudge(self, user_id: int, user_phone: str, current_time: datetime):
        """Check if user needs a gym nudge"""
        try:
            # Get last gym log
            result = self.supabase.table('gym_logs')\
                .select("*")\
                .eq('user_id', user_id)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if not result.data:
                # No gym logs at all - don't nudge (might be new user)
                return
            
            last_log = result.data[0]
            last_log_date_str = last_log.get('timestamp') or last_log.get('created_at')
            
            if not last_log_date_str:
                return
            
            try:
                last_log_date = datetime.fromisoformat(last_log_date_str.replace('Z', '+00:00'))
                if last_log_date.tzinfo is None:
                    last_log_date = last_log_date.replace(tzinfo=timedelta(hours=0))
                
                days_since = (current_time - last_log_date.replace(tzinfo=None)).days
                
                # Only nudge if it's been 2+ days
                if days_since >= 2:
                    message = f"It's been {days_since} days since your last workout - just a gentle reminder"
                    
                    result = self.communication_service.send_response(message, user_phone)
                    if result['success']:
                        logger.info(f"Gym nudge sent to user {user_id}")
            
            except Exception as e:
                logger.debug(f"Error parsing last gym date: {e}")
        
        except Exception as e:
            logger.debug(f"Error checking gym nudge: {e}")
    
    def send_weekly_digest(self):
        """Send weekly summary of behavior and progress"""
        try:
            if not self.config.WEEKLY_DIGEST_ENABLED:
                return
            
            today = datetime.now().date()
            
            # Calculate week boundaries (Monday to Sunday)
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Get all users with phone numbers
            result = self.supabase.table('users')\
                .select("*")\
                .not_.is_('phone_number', 'null')\
                .execute()
            
            users = result.data if result.data else []
            
            for user in users:
                try:
                    user_id = user['id']
                    user_phone = user.get('phone_number')
                    
                    if not user_phone or user_phone.startswith('web-'):
                        continue  # Skip web-only users
                    
                    # Get week's data
                    week_water = self._get_week_water(user_id, week_start, week_end)
                    week_food = self._get_week_food(user_id, week_start, week_end)
                    week_gym = self._get_week_gym(user_id, week_start, week_end)
                    week_todos = self._get_week_todos(user_id, week_start, week_end)
                    
                    prefs = self._get_prefs(user_id)
                    units = self._get_units(prefs)

                    # Calculate stats
                    total_water_ml = sum(float(log.get('amount_ml', 0)) for log in week_water)
                    avg_water_ml = total_water_ml / 7 if week_water else 0
                    
                    total_calories = sum(float(log.get('calories', 0)) * float(log.get('portion_multiplier', 1.0) or 1.0) for log in week_food)
                    total_protein = sum(float(log.get('protein', 0)) * float(log.get('portion_multiplier', 1.0) or 1.0) for log in week_food)
                    total_carbs = sum(float(log.get('carbs', 0)) * float(log.get('portion_multiplier', 1.0) or 1.0) for log in week_food)
                    total_fat = sum(float(log.get('fat', 0)) * float(log.get('portion_multiplier', 1.0) or 1.0) for log in week_food)
                    avg_calories = total_calories / 7 if week_food else 0
                    avg_protein = total_protein / 7 if week_food else 0
                    avg_carbs = total_carbs / 7 if week_food else 0
                    avg_fat = total_fat / 7 if week_food else 0
                    
                    gym_days = len(set(log.get('timestamp', '')[:10] for log in week_gym if log.get('timestamp')))
                    
                    completed_todos = sum(1 for todo in week_todos if todo.get('completed', False))
                    total_todos = len(week_todos)
                    completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
                    
                    # Build digest message
                    message = "📊 Weekly Digest:\n\n"
                    # Water vs goal (default goal)
                    goal_ml = self._get_water_goal_for_date(user_id, week_end.isoformat(), prefs) or prefs.get("default_water_goal_ml") or None
                    try:
                        goal_ml = int(goal_ml) if goal_ml else None
                    except Exception:
                        goal_ml = None
                    message += f"💧 Water: {self._format_water_amount(avg_water_ml, units)}/day avg"
                    if goal_ml:
                        message += f" (goal {self._format_water_amount(goal_ml, units)})"
                    message += "\n"

                    message += f"🍽️ Calories: {int(avg_calories)} /day avg"
                    if prefs.get("default_calories_goal"):
                        try:
                            message += f" (goal {int(prefs.get('default_calories_goal'))})"
                        except Exception:
                            pass
                    message += "\n"
                    # Macros
                    if avg_protein > 0 or prefs.get("default_protein_goal"):
                        message += f"🥩 Protein: {int(avg_protein)}g/day avg"
                        if prefs.get("default_protein_goal"):
                            try:
                                message += f" (goal {int(prefs.get('default_protein_goal'))}g)"
                            except Exception:
                                pass
                        message += "\n"
                    if avg_carbs > 0 or prefs.get("default_carbs_goal"):
                        message += f"🍞 Carbs: {int(avg_carbs)}g/day avg"
                        if prefs.get("default_carbs_goal"):
                            try:
                                message += f" (goal {int(prefs.get('default_carbs_goal'))}g)"
                            except Exception:
                                pass
                        message += "\n"
                    if avg_fat > 0 or prefs.get("default_fat_goal"):
                        message += f"🥑 Fat: {int(avg_fat)}g/day avg"
                        if prefs.get("default_fat_goal"):
                            try:
                                message += f" (goal {int(prefs.get('default_fat_goal'))}g)"
                            except Exception:
                                pass
                        message += "\n"

                    message += f"💪 Gym: {gym_days} day{'s' if gym_days != 1 else ''}\n"
                    message += f"✅ Tasks: {completed_todos}/{total_todos} completed ({int(completion_rate)}%)"
                    
                    result = self.communication_service.send_response(message, user_phone)
                    if result['success']:
                        logger.info(f"Weekly digest sent to user {user_id}")
                
                except Exception as e:
                    logger.error(f"Error sending weekly digest to user {user_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error sending weekly digest: {e}")
    
    def _get_week_water(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get water logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.water_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_food(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get food logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.food_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_gym(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get gym logs for the week"""
        logs = []
        current = week_start
        while current <= week_end:
            day_logs = self.gym_repo.get_by_date(user_id, current.isoformat())
            logs.extend(day_logs)
            current += timedelta(days=1)
        return logs
    
    def _get_week_todos(self, user_id: int, week_start, week_end) -> List[Dict]:
        """Get todos for the week"""
        # Get todos created or due during the week
        start_str = week_start.isoformat()
        end_str = (week_end + timedelta(days=1)).isoformat()
        
        result = self.supabase.table('reminders_todos')\
            .select("*")\
            .eq('user_id', user_id)\
            .gte('created_at', start_str)\
            .lte('created_at', end_str)\
            .execute()
        
        return result.data if result.data else []

    def send_weekly_digest_due(self):
        """Send weekly digest only for users whose preferences are due now."""
        if not self.config.WEEKLY_DIGEST_ENABLED:
            return

        now_utc = datetime.now(tz=ZoneInfo("UTC"))

        result = (
            self.supabase.table("users")
            .select("*")
            .not_.is_("phone_number", "null")
            .execute()
        )
        users = result.data if result.data else []

        for user in users:
            user_id = user["id"]
            user_phone = user.get("phone_number")
            if not user_phone or user_phone.startswith("web-"):
                continue

            prefs = self._get_prefs(user_id)
            user_tz = self._get_user_tz(user)
            if self._is_in_quiet_hours(prefs, user_tz, now_utc):
                continue

            # desired schedule (defaults to config)
            wd = prefs.get("weekly_digest_day")
            wh = prefs.get("weekly_digest_hour")
            try:
                wd = int(wd) if wd is not None else None
                wh = int(wh) if wh is not None else None
            except Exception:
                wd = None
                wh = None

            local_now = now_utc.astimezone(user_tz)
            desired_weekday = wd if wd is not None else self.config.WEEKLY_DIGEST_DAY
            desired_hour = wh if wh is not None else self.config.WEEKLY_DIGEST_HOUR

            if local_now.weekday() != desired_weekday or local_now.hour != desired_hour:
                continue

            last_sent = prefs.get("last_weekly_digest_sent_at")
            if last_sent:
                try:
                    last_dt = datetime.fromisoformat(str(last_sent).replace("Z", "+00:00"))
                    if (now_utc - last_dt).days < 6:
                        continue
                except Exception:
                    pass

            today = local_now.date()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)

            week_water = self._get_week_water(user_id, week_start, week_end)
            week_food = self._get_week_food(user_id, week_start, week_end)
            week_gym = self._get_week_gym(user_id, week_start, week_end)
            week_todos = self._get_week_todos(user_id, week_start, week_end)

            total_water_ml = sum(float(log.get("amount_ml", 0)) for log in week_water)
            avg_water_ml = total_water_ml / 7 if week_water else 0
            total_calories = sum(float(log.get("calories", 0)) * float(log.get("portion_multiplier", 1.0) or 1.0) for log in week_food)
            total_protein = sum(float(log.get("protein", 0)) * float(log.get("portion_multiplier", 1.0) or 1.0) for log in week_food)
            total_carbs = sum(float(log.get("carbs", 0)) * float(log.get("portion_multiplier", 1.0) or 1.0) for log in week_food)
            total_fat = sum(float(log.get("fat", 0)) * float(log.get("portion_multiplier", 1.0) or 1.0) for log in week_food)
            avg_calories = total_calories / 7 if week_food else 0
            avg_protein = total_protein / 7 if week_food else 0
            avg_carbs = total_carbs / 7 if week_food else 0
            avg_fat = total_fat / 7 if week_food else 0
            gym_days = len(set((log.get("timestamp", "") or "")[:10] for log in week_gym if log.get("timestamp")))
            completed_todos = sum(1 for todo in week_todos if todo.get("completed", False))
            total_todos = len(week_todos)
            completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0

            units = self._get_units(prefs)
            goal_ml = self._get_water_goal_for_date(user_id, week_end.isoformat(), prefs) or prefs.get("default_water_goal_ml") or None
            try:
                goal_ml = int(goal_ml) if goal_ml else None
            except Exception:
                goal_ml = None

            message = "📊 Weekly Digest:\n\n"
            message += f"💧 Water: {self._format_water_amount(avg_water_ml, units)}/day avg"
            if goal_ml:
                message += f" (goal {self._format_water_amount(goal_ml, units)})"
            message += "\n"

            message += f"🍽️ Calories: {int(avg_calories)} /day avg"
            if prefs.get("default_calories_goal"):
                try:
                    message += f" (goal {int(prefs.get('default_calories_goal'))})"
                except Exception:
                    pass
            message += "\n"

            if avg_protein > 0 or prefs.get("default_protein_goal"):
                message += f"🥩 Protein: {int(avg_protein)}g/day avg"
                if prefs.get("default_protein_goal"):
                    try:
                        message += f" (goal {int(prefs.get('default_protein_goal'))}g)"
                    except Exception:
                        pass
                message += "\n"
            if avg_carbs > 0 or prefs.get("default_carbs_goal"):
                message += f"🍞 Carbs: {int(avg_carbs)}g/day avg"
                if prefs.get("default_carbs_goal"):
                    try:
                        message += f" (goal {int(prefs.get('default_carbs_goal'))}g)"
                    except Exception:
                        pass
                message += "\n"
            if avg_fat > 0 or prefs.get("default_fat_goal"):
                message += f"🥑 Fat: {int(avg_fat)}g/day avg"
                if prefs.get("default_fat_goal"):
                    try:
                        message += f" (goal {int(prefs.get('default_fat_goal'))}g)"
                    except Exception:
                        pass
                message += "\n"

            message += f"💪 Gym: {gym_days} day{'s' if gym_days != 1 else ''}\n"
            message += f"✅ Tasks: {completed_todos}/{total_todos} completed ({int(completion_rate)}%)"

            result = self.communication_service.send_response(message, user_phone)
            if result.get("success"):
                try:
                    self.user_prefs_repo.update(user_id, {"last_weekly_digest_sent_at": now_utc.isoformat()})
                except Exception:
                    pass
                logger.info(f"Weekly digest sent to user {user_id}")

    def send_morning_checkins_due(self):
        """Send morning check-in messages for users whose local time matches their preference."""
        now_utc = datetime.now(tz=ZoneInfo("UTC"))

        result = (
            self.supabase.table("users")
            .select("*")
            .not_.is_("phone_number", "null")
            .execute()
        )
        users = result.data if result.data else []

        for user in users:
            user_id = user["id"]
            user_phone = user.get("phone_number")
            if not user_phone or user_phone.startswith("web-"):
                continue

            prefs = self._get_prefs(user_id)
            user_tz = self._get_user_tz(user)
            if self._is_in_quiet_hours(prefs, user_tz, now_utc):
                continue

            local_now = now_utc.astimezone(user_tz)
            desired_hour = user.get("morning_checkin_hour")
            try:
                desired_hour = int(desired_hour) if desired_hour is not None else None
            except Exception:
                desired_hour = None
            if desired_hour is None:
                desired_hour = self.config.MORNING_CHECKIN_HOUR

            if local_now.hour != desired_hour:
                continue

            last_sent = prefs.get("last_morning_checkin_sent_at")
            if last_sent:
                try:
                    last_dt = datetime.fromisoformat(str(last_sent).replace("Z", "+00:00"))
                    if last_dt.astimezone(user_tz).date() == local_now.date():
                        continue
                except Exception:
                    pass

            include_reminders = prefs.get("morning_include_reminders", True) if prefs else True
            include_weather = prefs.get("morning_include_weather", True) if prefs else True
            include_quote = prefs.get("morning_include_quote", True) if prefs else True

            parts: List[str] = []
            name = (user.get("name") or "").strip()
            parts.append(f"Good morning{', ' + name if name else ''}.")

            if include_reminders:
                today = local_now.date().isoformat()
                due_today = self.todo_repo.get_by_date(user_id, today)
                due_soon = self.todo_repo.get_due_soon(user_id, hours=12)
                if due_today:
                    parts.append(f"Today: {len(due_today)} item{'s' if len(due_today) != 1 else ''} due.")
                elif due_soon:
                    parts.append(f"Next up: {len(due_soon)} item{'s' if len(due_soon) != 1 else ''} due soon.")
                else:
                    parts.append("No deadlines on the radar right now.")

            if include_weather:
                wline = self._get_weather_line(user, prefs)
                if wline:
                    parts.append(wline)

            if include_quote:
                q = self._pick_daily_quote(user_id, local_now.date().isoformat())
                if q:
                    parts.append(q)

            # Add a small progress line (water + calories/macros) when reminders section is enabled
            if include_reminders:
                units = self._get_units(prefs)
                today = local_now.date().isoformat()
                # Totals so far today
                water_logs = self.water_repo.get_by_date(user_id, today)
                total_water_ml = sum(float(l.get("amount_ml", 0) or 0) for l in water_logs)
                food_logs = self.food_repo.get_by_date(user_id, today)
                total_cal = sum(float(l.get("calories", 0) or 0) * float(l.get("portion_multiplier", 1.0) or 1.0) for l in food_logs)
                total_pro = sum(float(l.get("protein", 0) or 0) * float(l.get("portion_multiplier", 1.0) or 1.0) for l in food_logs)
                total_car = sum(float(l.get("carbs", 0) or 0) * float(l.get("portion_multiplier", 1.0) or 1.0) for l in food_logs)
                total_fat = sum(float(l.get("fat", 0) or 0) * float(l.get("portion_multiplier", 1.0) or 1.0) for l in food_logs)

                water_goal = self._get_water_goal_for_date(user_id, today, prefs)
                water_prog = self._format_water_progress(total_water_ml, water_goal, units)
                prog_parts = [f"Progress: water {water_prog}"]
                if prefs.get("default_calories_goal"):
                    try:
                        prog_parts.append(f"cal {int(total_cal)}/{int(prefs.get('default_calories_goal'))}")
                    except Exception:
                        prog_parts.append(f"cal {int(total_cal)}")
                else:
                    prog_parts.append(f"cal {int(total_cal)}")
                if prefs.get("default_protein_goal"):
                    try:
                        prog_parts.append(f"protein {int(total_pro)}/{int(prefs.get('default_protein_goal'))}g")
                    except Exception:
                        prog_parts.append(f"protein {int(total_pro)}g")
                else:
                    prog_parts.append(f"protein {int(total_pro)}g")

                # Only include carbs/fat if goals set (keeps it short)
                if prefs.get("default_carbs_goal"):
                    try:
                        prog_parts.append(f"carbs {int(total_car)}/{int(prefs.get('default_carbs_goal'))}g")
                    except Exception:
                        pass
                if prefs.get("default_fat_goal"):
                    try:
                        prog_parts.append(f"fat {int(total_fat)}/{int(prefs.get('default_fat_goal'))}g")
                    except Exception:
                        pass

                parts.append(" | ".join(prog_parts))

            message = "\n".join(parts)
            result = self.communication_service.send_response(message, user_phone)
            if result.get("success"):
                try:
                    self.user_prefs_repo.update(user_id, {"last_morning_checkin_sent_at": now_utc.isoformat()})
                except Exception:
                    pass
                logger.info(f"Morning check-in sent to user {user_id}")
