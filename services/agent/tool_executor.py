"""
Validated tool execution layer for the agent.

This module is intentionally conservative:
- Validates inputs (types, bounds)
- Caps fan-out (limits, days, tool calls)
- Only uses vetted repository operations (no arbitrary SQL)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from supabase import Client

from data import (
    AssignmentRepository,
    FoodRepository,
    GymRepository,
    SleepRepository,
    TodoRepository,
    UserPreferencesRepository,
    UserRepository,
    WaterRepository,
    UserMemoryStateRepository,
    UserMemoryItemsRepository,
)


class ToolValidationError(ValueError):
    pass


def _as_int(x: Any, *, name: str) -> int:
    try:
        return int(x)
    except Exception:
        raise ToolValidationError(f"{name} must be an integer")


def _as_float(x: Any, *, name: str) -> float:
    try:
        return float(x)
    except Exception:
        raise ToolValidationError(f"{name} must be a number")


def _as_str(x: Any, *, name: str) -> str:
    s = ("" if x is None else str(x)).strip()
    if not s:
        raise ToolValidationError(f"{name} is required")
    return s


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))


@dataclass
class ToolExecutionResult:
    name: str
    ok: bool
    result: Any = None
    error: Optional[str] = None


class ToolExecutor:
    """
    Executes a small set of safe tools against Supabase.
    """

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.user_repo = UserRepository(supabase)
        self.prefs_repo = UserPreferencesRepository(supabase)
        self.food_repo = FoodRepository(supabase)
        self.water_repo = WaterRepository(supabase)
        self.gym_repo = GymRepository(supabase)
        self.sleep_repo = SleepRepository(supabase)
        self.todo_repo = TodoRepository(supabase)
        self.assignment_repo = AssignmentRepository(supabase)
        self.memory_state_repo = UserMemoryStateRepository(supabase)
        self.memory_items_repo = UserMemoryItemsRepository(supabase)

    # ---------------------------------------------------------------------
    # Public entrypoint
    # ---------------------------------------------------------------------
    def execute(self, *, user_id: int, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        fn = getattr(self, f"_tool_{tool_name}", None)
        if fn is None:
            return ToolExecutionResult(name=tool_name, ok=False, error="Unknown tool")
        try:
            out = fn(user_id=user_id, **(arguments or {}))
            return ToolExecutionResult(name=tool_name, ok=True, result=out)
        except ToolValidationError as e:
            return ToolExecutionResult(name=tool_name, ok=False, error=str(e))
        except Exception as e:
            return ToolExecutionResult(name=tool_name, ok=False, error=str(e))

    # ---------------------------------------------------------------------
    # Read tools
    # ---------------------------------------------------------------------
    def _tool_get_user_profile(self, *, user_id: int) -> Dict[str, Any]:
        u = self.user_repo.get_by_id(int(user_id)) or {}
        return {
            "user_id": u.get("id"),
            "name": u.get("name"),
            "timezone": u.get("timezone"),
            "location_name": u.get("location_name"),
            "plan": u.get("plan", "free"),
            "plan_interval": u.get("plan_interval"),
        }

    def _tool_get_user_preferences(self, *, user_id: int) -> Dict[str, Any]:
        self.prefs_repo.ensure(int(user_id))
        return self.prefs_repo.get(int(user_id)) or {}

    def _tool_get_memory_summary(self, *, user_id: int) -> Dict[str, Any]:
        row = self.memory_state_repo.ensure(int(user_id))
        return {
            "summary": row.get("summary") or "",
            "style_profile": row.get("style_profile") or {},
            "summary_updated_at": row.get("summary_updated_at"),
        }

    def _tool_search_memory(self, *, user_id: int, query: str, top_k: Any = 10) -> Dict[str, Any]:
        q = _as_str(query, name="query")
        k = _clamp(_as_int(top_k, name="top_k"), 1, 20)
        # Keyword fallback. Embedding-based semantic search will be added in the orchestrator phase.
        hits = self.memory_items_repo.keyword_search(int(user_id), q, limit=k)
        return {"query": q, "results": hits}

    def _tool_get_recent_activity(
        self,
        *,
        user_id: int,
        types: Optional[List[str]] = None,
        days: Any = 7,
        limit: Any = 50,
    ) -> Dict[str, Any]:
        d = _clamp(_as_int(days, name="days"), 1, 365)
        lim = _clamp(_as_int(limit, name="limit"), 1, 200)
        want = set([t.strip() for t in (types or []) if t and str(t).strip()])

        end_d = date.today()
        start_d = end_d - timedelta(days=d - 1)
        start_date = start_d.isoformat()
        end_date = end_d.isoformat()

        def _safe_iso(dt_str: str) -> str:
            if not dt_str:
                return ""
            return str(dt_str).replace(" ", "T")

        items: List[Dict[str, Any]] = []

        def _push(t: str, timestamp: str, title: str, subtitle: str):
            if want and t not in want:
                return
            items.append({"type": t, "timestamp": timestamp, "title": title, "subtitle": subtitle})

        # Food
        try:
            for log in (self.food_repo.get_by_date_range(int(user_id), start_date, end_date) or []):
                ts = _safe_iso(log.get("timestamp"))
                title = (log.get("food_name") or "Food").strip()
                kcal = log.get("calories")
                pm = float(log.get("portion_multiplier") or 1.0)
                sub = "Food log"
                if kcal is not None:
                    try:
                        sub = f"{int(float(kcal) * pm)} cal"
                    except Exception:
                        sub = f"{kcal} cal"
                rest = log.get("restaurant")
                if rest:
                    sub = sub + f" • {rest}"
                _push("food", ts, title, sub)
        except Exception:
            pass

        # Water
        try:
            for log in (self.water_repo.get_by_date_range(int(user_id), start_date, end_date) or []):
                ts = _safe_iso(log.get("timestamp"))
                amt = log.get("amount_ml")
                sub = f"{amt} ml" if amt is not None else "Water log"
                _push("water", ts, "Water", sub)
        except Exception:
            pass

        # Workouts
        try:
            for log in (self.gym_repo.get_by_date_range(int(user_id), start_date, end_date) or []):
                ts = _safe_iso(log.get("timestamp"))
                ex = (log.get("exercise") or "Workout").strip()
                sets = log.get("sets")
                reps = log.get("reps")
                parts = []
                if sets and reps:
                    parts.append(f"{sets}×{reps}")
                elif sets:
                    parts.append(f"{sets} sets")
                w = log.get("weight")
                if w is not None and w != "":
                    parts.append(f"@ {w}")
                _push("workout", ts, ex, " • ".join(parts) if parts else "Workout log")
        except Exception:
            pass

        # Sleep
        try:
            for log in (self.sleep_repo.get_by_date_range(int(user_id), start_date, end_date) or []):
                dte = log.get("date") or ""
                wake = log.get("wake_time") or "00:00:00"
                ts = _safe_iso(f"{dte}T{wake}") if dte else ""
                dur = log.get("duration_hours")
                sub = f"{dur} hours" if dur is not None else "Sleep log"
                _push("sleep", ts, "Sleep", sub)
        except Exception:
            pass

        # Todos/reminders (direct query to capture timestamps)
        try:
            start_ts = f"{start_date}T00:00:00"
            end_ts = f"{end_date}T23:59:59.999999"
            res = (
                self.supabase.table("reminders_todos")
                .select("*")
                .eq("user_id", int(user_id))
                .gte("timestamp", start_ts)
                .lte("timestamp", end_ts)
                .order("timestamp", desc=True)
                .limit(200)
                .execute()
            )
            for log in (res.data or []):
                ts = _safe_iso(log.get("timestamp"))
                ttype = (log.get("type") or "todo")
                title = "Reminder" if ttype == "reminder" else "Todo"
                content = (log.get("content") or "").strip()
                _push(ttype, ts, title, content or title)
        except Exception:
            pass

        # Sort + cap
        def _dt_key(ts: str) -> datetime:
            if not ts:
                return datetime.min
            s = str(ts).replace("Z", "+00:00")
            if len(s) == 10:
                s = s + "T00:00:00"
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return datetime.min

        items.sort(key=lambda x: _dt_key(x.get("timestamp") or ""), reverse=True)
        return {"start_date": start_date, "end_date": end_date, "items": items[:lim]}

    def _tool_get_assignments_due(self, *, user_id: int, days: Any = 14) -> Dict[str, Any]:
        d = _clamp(_as_int(days, name="days"), 1, 90)
        overdue = self.assignment_repo.get_overdue(int(user_id))
        due_soon = self.assignment_repo.get_due_soon(int(user_id), days=d)
        items = []
        for a in (overdue or []):
            items.append({
                "assignment_name": a.get("assignment_name"),
                "class_name": a.get("class_name"),
                "due_date": a.get("due_date"),
                "overdue": True,
            })
        for a in (due_soon or []):
            items.append({
                "assignment_name": a.get("assignment_name"),
                "class_name": a.get("class_name"),
                "due_date": a.get("due_date"),
                "overdue": False,
            })
        items.sort(key=lambda x: (x.get("due_date") or ""))
        return {"assignments": items, "days_ahead": d}

    def _tool_get_week_summary(self, *, user_id: int) -> Dict[str, Any]:
        prefs = self.prefs_repo.get(int(user_id)) or {}
        goals = {
            "water_ml": prefs.get("default_water_goal_ml"),
            "calories": prefs.get("default_calories_goal"),
            "protein_g": prefs.get("default_protein_goal"),
        }
        stats = {}
        for m in ["water", "calories", "protein", "workouts", "sleep"]:
            try:
                r = self._tool_get_stats(user_id=user_id, metric=m, timeframe_days=7)
                stats[m] = r.get("total")
            except Exception:
                stats[m] = None
        return {"stats_7_days": stats, "goals": goals}

    def _tool_get_today_summary(self, *, user_id: int) -> Dict[str, Any]:
        prefs = self.prefs_repo.get(int(user_id)) or {}
        goals = {
            "water_ml": prefs.get("default_water_goal_ml"),
            "calories": prefs.get("default_calories_goal"),
            "protein_g": prefs.get("default_protein_goal"),
        }
        stats = {}
        for m in ["water", "calories", "protein", "workouts", "sleep"]:
            try:
                r = self._tool_get_stats(user_id=user_id, metric=m, timeframe_days=1)
                stats[m] = r.get("total")
            except Exception:
                stats[m] = None
        return {"stats_today": stats, "goals": goals}

    def _tool_get_stats(self, *, user_id: int, metric: str, timeframe_days: Any = 7) -> Dict[str, Any]:
        m = (metric or "").strip().lower()
        days = _clamp(_as_int(timeframe_days, name="timeframe_days"), 1, 365)
        end_d = date.today()
        start_d = end_d - timedelta(days=days - 1)
        start_date = start_d.isoformat()
        end_date = end_d.isoformat()

        def _num(x: Any) -> float:
            try:
                return float(x)
            except Exception:
                return 0.0

        if m == "water":
            logs = self.water_repo.get_by_date_range(int(user_id), start_date, end_date)
            total_ml = sum(_num(l.get("amount_ml")) for l in (logs or []))
            return {"metric": "water", "unit": "ml", "total": round(total_ml, 1), "days": days}

        if m in {"calories", "protein", "carbs", "fat"}:
            logs = self.food_repo.get_by_date_range(int(user_id), start_date, end_date)
            total = 0.0
            for l in (logs or []):
                pm = _num(l.get("portion_multiplier") or 1.0) or 1.0
                total += _num(l.get(m)) * pm
            unit = "cal" if m == "calories" else "g"
            return {"metric": m, "unit": unit, "total": round(total, 1), "days": days}

        if m == "workouts":
            logs = self.gym_repo.get_by_date_range(int(user_id), start_date, end_date)
            return {"metric": "workouts", "unit": "sessions", "total": len(logs or []), "days": days}

        if m == "sleep":
            logs = self.sleep_repo.get_by_date_range(int(user_id), start_date, end_date)
            total = sum(_num(l.get("duration_hours")) for l in (logs or []))
            return {"metric": "sleep", "unit": "hours", "total": round(total, 1), "days": days}

        if m == "todos":
            # completed count in range
            start_ts = f"{start_date}T00:00:00"
            end_ts = f"{end_date}T23:59:59.999999"
            res = (
                self.supabase.table("reminders_todos")
                .select("id", count="exact")
                .eq("user_id", int(user_id))
                .eq("completed", True)
                .gte("completed_at", start_ts)
                .lte("completed_at", end_ts)
                .execute()
            )
            cnt = getattr(res, "count", None)
            return {"metric": "todos", "unit": "completed", "total": int(cnt or 0), "days": days}

        raise ToolValidationError("metric must be one of: water, calories, protein, carbs, fat, workouts, sleep, todos")

    # ---------------------------------------------------------------------
    # Write tools
    # ---------------------------------------------------------------------
    def _tool_log_water(self, *, user_id: int, amount_ml: Any, source: Optional[str] = None) -> Dict[str, Any]:
        ml = _as_float(amount_ml, name="amount_ml")
        if ml <= 0 or ml > 20000:
            raise ToolValidationError("amount_ml must be between 1 and 20000")
        row = self.water_repo.create_water_log(int(user_id), amount_ml=ml)
        return {"created": row, "source": source}

    def _tool_log_food(self, *, user_id: int, items: Any, source: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not isinstance(items, list) or not items:
            raise ToolValidationError("items must be a non-empty list")
        if len(items) > 10:
            raise ToolValidationError("items max length is 10")

        created = []
        for it in items:
            if not isinstance(it, dict):
                raise ToolValidationError("each item must be an object")
            food_name = _as_str(it.get("food_name"), name="food_name")
            calories = _as_float(it.get("calories", 0), name="calories")
            protein = _as_float(it.get("protein", 0), name="protein")
            carbs = _as_float(it.get("carbs", 0), name="carbs")
            fat = _as_float(it.get("fat", 0), name="fat")
            restaurant = (it.get("restaurant") or None)
            portion_multiplier = _as_float(it.get("portion_multiplier", 1.0), name="portion_multiplier")
            if portion_multiplier <= 0:
                portion_multiplier = 1.0
            row = self.food_repo.create_food_log(
                int(user_id),
                food_name=food_name,
                calories=calories,
                protein=protein,
                carbs=carbs,
                fat=fat,
                restaurant=restaurant,
                portion_multiplier=portion_multiplier,
            )
            created.append(row)
        return {"created": created, "source": source, "metadata": metadata or {}}

    def _tool_add_todo(self, *, user_id: int, text: str, due_at: Optional[str] = None) -> Dict[str, Any]:
        content = _as_str(text, name="text")
        due = None
        if due_at:
            s = str(due_at).strip().replace("Z", "+00:00")
            try:
                due = datetime.fromisoformat(s)
            except Exception:
                raise ToolValidationError("due_at must be ISO8601 datetime if provided")
        row = self.todo_repo.create_todo(int(user_id), content=content, due_date=due, type="todo")
        return {"created": row}

    def _tool_add_reminder(self, *, user_id: int, content: str, due_at: Optional[str] = None) -> Dict[str, Any]:
        text = _as_str(content, name="content")
        due = None
        if due_at:
            s = str(due_at).strip().replace("Z", "+00:00")
            try:
                due = datetime.fromisoformat(s)
            except Exception:
                raise ToolValidationError("due_at must be ISO8601 datetime if provided")
        row = self.todo_repo.create_todo(int(user_id), content=text, due_date=due, type="reminder")
        return {"created": row}

    def _tool_log_sleep(
        self,
        *,
        user_id: int,
        date_str: Optional[str] = None,
        duration_hours: Any = None,
        sleep_time_str: Optional[str] = None,
        wake_time_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        d = date_str
        if not d or not str(d).strip():
            d = date.today().isoformat()
        else:
            try:
                datetime.strptime(str(d).strip()[:10], "%Y-%m-%d")
            except Exception:
                raise ToolValidationError("date_str must be YYYY-MM-DD")
            d = str(d).strip()[:10]
        dur = _as_float(duration_hours, name="duration_hours")
        if dur <= 0 or dur > 24:
            raise ToolValidationError("duration_hours must be between 0 and 24")
        st_str = (sleep_time_str or "").strip() or "00:00"
        wt_str = (wake_time_str or "").strip()
        if not wt_str:
            # Derive wake from duration: 00:00 + duration_hours
            h = int(dur)
            m = int(round((dur - h) * 60))
            wt_str = f"{h:02d}:{m:02d}:00"
        for s, name in [(st_str, "sleep_time"), (wt_str, "wake_time")]:
            if len(s) == 5 and ":" in s:
                s = s + ":00"
            if len(s) < 8:
                raise ToolValidationError(f"{name} must be HH:MM or HH:MM:SS")
            try:
                time.fromisoformat(s)
            except Exception:
                raise ToolValidationError(f"{name} must be valid time HH:MM or HH:MM:SS")
        if len(st_str) == 5:
            st_str = st_str + ":00"
        if len(wt_str) == 5:
            wt_str = wt_str + ":00"
        st = time.fromisoformat(st_str)
        wt = time.fromisoformat(wt_str)
        row = self.sleep_repo.create_sleep_log(int(user_id), d, st, wt, dur)
        return {"created": row}

    def _tool_log_workout(
        self,
        *,
        user_id: int,
        exercise: str,
        sets: Optional[Any] = None,
        reps: Optional[Any] = None,
        weight: Optional[Any] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        ex = _as_str(exercise, name="exercise")
        s = int(sets) if sets is not None else None
        r = int(reps) if reps is not None else None
        w = float(weight) if weight is not None else None
        if s is not None and (s < 0 or s > 999):
            raise ToolValidationError("sets must be 0-999")
        if r is not None and (r < 0 or r > 9999):
            raise ToolValidationError("reps must be 0-9999")
        row = self.gym_repo.create_gym_log(int(user_id), exercise=ex, sets=s, reps=r, weight=w, notes=notes)
        return {"created": row}

    def _tool_set_preference(self, *, user_id: int, key: str, value: Any) -> Dict[str, Any]:
        k = _as_str(key, name="key")
        allowed = {
            "units",
            "response_style",
            "freeform_goal",
            "quiet_hours_start",
            "quiet_hours_end",
            "do_not_disturb",
            "weekly_digest_day",
            "weekly_digest_hour",
            "default_water_goal_ml",
            "default_calories_goal",
            "default_protein_goal",
            "default_carbs_goal",
            "default_fat_goal",
            "morning_include_reminders",
            "morning_include_weather",
            "morning_include_quote",
        }
        if k not in allowed:
            raise ToolValidationError("Unsupported preference key")

        # Basic coercions mirroring dashboard API
        v = value
        if k in {"quiet_hours_start", "quiet_hours_end", "weekly_digest_day", "weekly_digest_hour"}:
            v = _as_int(v, name="value")
        if k in {"default_water_goal_ml", "default_calories_goal", "default_protein_goal", "default_carbs_goal", "default_fat_goal"}:
            v = int(float(v))
        if k in {"do_not_disturb", "morning_include_reminders", "morning_include_weather", "morning_include_quote"}:
            v = bool(v)
        if k == "units" and v not in ("metric", "imperial"):
            raise ToolValidationError("units must be metric or imperial")
        if k == "response_style" and v not in ("concise", "friendly", "detailed"):
            raise ToolValidationError("response_style must be concise, friendly, or detailed")
        if k == "freeform_goal":
            v = str(v).strip() if v is not None else None

        self.prefs_repo.ensure(int(user_id))
        row = self.prefs_repo.update(int(user_id), {k: v})
        return {"updated": row, "key": k, "value": v}

    def _tool_append_memory_item(self, *, user_id: int, kind: str, content: str, importance: Any = 0.5, source: Optional[str] = None) -> Dict[str, Any]:
        k = _as_str(kind, name="kind")
        c = _as_str(content, name="content")
        imp = _as_float(importance, name="importance")
        if imp < 0:
            imp = 0.0
        if imp > 1:
            imp = 1.0
        if len(c) > 2000:
            raise ToolValidationError("content too long (max 2000 chars)")
        row = self.memory_items_repo.create_item(int(user_id), kind=k, content=c, source=source, importance=imp)
        return {"created": row}

