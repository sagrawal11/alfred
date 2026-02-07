"""
Query Handler
Handles stats queries, fact storage, and fact queries
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Dict, Optional

from supabase import Client

from core.context import ConversationContext
from data import FactRepository, UserPreferencesRepository
from handlers.base_handler import BaseHandler


class QueryHandler(BaseHandler):
    """Handles queries, stats, and facts"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.fact_repo = FactRepository(supabase)
        self.prefs_repo = UserPreferencesRepository(supabase)
    
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle query intents"""
        if intent == 'stats_query':
            return self._handle_stats_query(message, user_id, context)
        elif intent == 'what_should_i_do':
            return self._handle_suggestion(message, user_id, context, focus='any')
        elif intent == 'food_suggestion':
            return self._handle_suggestion(message, user_id, context, focus='food')
        elif intent == 'fact_storage':
            return self._handle_fact_storage(message, user_id)
        elif intent == 'fact_query':
            return self._handle_fact_query(message, user_id)
        else:
            return None
    
    def _handle_stats_query(self, message: str, user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle stats queries"""
        # Parse what stats user wants
        stats_query = self.parser.parse_stats_query(message)
        
        # Get today's summary
        today_summary = context.get_today_summary()
        prefs = {}
        try:
            prefs = self.prefs_repo.get(user_id) or {}
        except Exception:
            prefs = {}
        cal_goal = prefs.get('default_calories_goal')
        protein_goal = prefs.get('default_protein_goal')
        carbs_goal = prefs.get('default_carbs_goal')
        fat_goal = prefs.get('default_fat_goal')
        units = prefs.get('units') if prefs else None
        if units not in ('metric', 'imperial'):
            units = 'metric'
        water_goal_default = prefs.get('default_water_goal_ml') if prefs else None
        try:
            water_goal_default = int(water_goal_default) if water_goal_default else None
        except Exception:
            water_goal_default = None

        # Water goal for today (per-day override if set)
        water_goal_ml = None
        try:
            today_utc = datetime.now(dt_timezone.utc).date().isoformat()
            wg = (
                self.supabase.table('water_goals')
                .select('goal_ml')
                .eq('user_id', user_id)
                .eq('date', today_utc)
                .limit(1)
                .execute()
            )
            if wg.data and wg.data[0].get('goal_ml') is not None:
                water_goal_ml = int(float(wg.data[0]['goal_ml']))
        except Exception:
            water_goal_ml = None
        if water_goal_ml is None:
            water_goal_ml = water_goal_default
        
        # Build response based on what user asked for
        response_parts = []
        
        if stats_query.get('all') or stats_query.get('food'):
            food = today_summary['food']
            if food['count'] > 0:
                line = f"Food: {food['count']} items, {int(food['calories'])} cal"
                if cal_goal:
                    try:
                        line += f" ({int(food['calories'])}/{int(cal_goal)})"
                    except Exception:
                        pass
                response_parts.append(line)
                # Include protein progress if available
                if food.get('protein') is not None:
                    p_line = f"Protein: {int(food['protein'])}g"
                    if protein_goal:
                        try:
                            p_line += f" ({int(food['protein'])}/{int(protein_goal)})"
                        except Exception:
                            pass
                    response_parts.append(p_line)
                if food.get('carbs') is not None:
                    c_line = f"Carbs: {int(food['carbs'])}g"
                    if carbs_goal:
                        try:
                            c_line += f" ({int(food['carbs'])}/{int(carbs_goal)})"
                        except Exception:
                            pass
                    response_parts.append(c_line)
                if food.get('fat') is not None:
                    f_line = f"Fat: {int(food['fat'])}g"
                    if fat_goal:
                        try:
                            f_line += f" ({int(food['fat'])}/{int(fat_goal)})"
                        except Exception:
                            pass
                    response_parts.append(f_line)
        
        if stats_query.get('all') or stats_query.get('water'):
            water = today_summary['water']
            if water['count'] > 0:
                total_ml = float(water.get('ml', 0) or 0)
                if units == 'imperial':
                    total_oz = total_ml / 29.5735
                    if water_goal_ml:
                        goal_oz = float(water_goal_ml) / 29.5735
                        response_parts.append(f"Water: {total_oz:.0f}oz ({total_oz:.0f}/{goal_oz:.0f})")
                    else:
                        response_parts.append(f"Water: {total_oz:.0f}oz")
                else:
                    total_l = total_ml / 1000.0
                    if water_goal_ml:
                        goal_l = float(water_goal_ml) / 1000.0
                        response_parts.append(f"Water: {total_l:.1f}L ({total_l:.1f}/{goal_l:.1f})")
                    else:
                        response_parts.append(f"Water: {total_l:.1f}L")
        
        if stats_query.get('all') or stats_query.get('gym'):
            gym = today_summary['gym']
            if gym['count'] > 0:
                response_parts.append(f"Workouts: {gym['count']}")
        
        if stats_query.get('todos'):
            todos = today_summary['todos']
            if todos['incomplete'] > 0:
                response_parts.append(f"Todos: {todos['incomplete']} incomplete")
        
        if not response_parts:
            # Friendly empty-state messages when they asked for one category
            only_food = stats_query.get('food') and not stats_query.get('all') and not stats_query.get('water') and not stats_query.get('gym') and not stats_query.get('todos')
            only_water = stats_query.get('water') and not stats_query.get('all') and not stats_query.get('food') and not stats_query.get('gym') and not stats_query.get('todos')
            only_gym = stats_query.get('gym') and not stats_query.get('all') and not stats_query.get('food') and not stats_query.get('water') and not stats_query.get('todos')
            only_todos = stats_query.get('todos') and not stats_query.get('all') and not stats_query.get('food') and not stats_query.get('water') and not stats_query.get('gym')
            if only_food and today_summary['food']['count'] == 0:
                return "No food logged today yet — start whenever you're ready."
            if only_water and today_summary['water']['count'] == 0:
                return "No water logged today yet — try \"drank a bottle\" when you do."
            if only_gym and today_summary['gym']['count'] == 0:
                return "No workouts logged today yet — whenever you're ready, just tell me what you did."
            if only_todos and today_summary['todos']['incomplete'] == 0:
                return "No todos yet — just tell me what you need to do and I'll add it."
            return "Nothing logged for today yet — start whenever you're ready!"
        
        return "\n".join(response_parts)
    
    def _handle_suggestion(
        self,
        message: str,
        user_id: int,
        context: ConversationContext,
        focus: str = 'any',
    ) -> Optional[str]:
        """Suggest workout and/or food based on user history, goals, and message. focus: 'any', 'food', 'workout'."""
        today_utc = datetime.now(dt_timezone.utc).date()
        start_7 = (today_utc - timedelta(days=7)).isoformat()
        end_today = today_utc.isoformat()
        
        today_summary = context.get_today_summary()
        prefs = {}
        try:
            prefs = self.prefs_repo.get(user_id) or {}
        except Exception:
            prefs = {}
        
        recent_gym = context.gym_repo.get_by_date_range(user_id, start_7, end_today)
        recent_food = context.food_repo.get_by_date_range(user_id, start_7, end_today)
        
        # Build a short summary of recent workouts (exercise names, last 7 days)
        gym_summary_parts = []
        by_date: Dict[str, list] = {}
        for log in recent_gym:
            ts = log.get('timestamp') or ''
            date_str = ts[:10] if len(ts) >= 10 else ''
            if date_str not in by_date:
                by_date[date_str] = []
            ex = (log.get('exercise') or '').strip()
            if ex:
                by_date[date_str].append(ex)
        for d in sorted(by_date.keys(), reverse=True)[:5]:
            gym_summary_parts.append(f"{d}: {', '.join(by_date[d][:5])}")
        recent_workouts_str = "; ".join(gym_summary_parts) if gym_summary_parts else "No recent workouts"
        
        # Today's food
        food = today_summary.get('food', {})
        today_food_str = (
            f"Today: {food.get('count', 0)} items, {int(food.get('calories', 0))} cal"
            + (f", {int(food.get('protein', 0))}g protein" if food.get('protein') is not None else "")
        )
        cal_goal = prefs.get('default_calories_goal')
        protein_goal = prefs.get('default_protein_goal')
        if cal_goal:
            today_food_str += f" (goal {int(cal_goal)} cal)"
        if protein_goal:
            today_food_str += f" (protein goal {int(protein_goal)}g)"
        
        # Exercise list from gym DB (sample for suggestions)
        exercise_sample: list = []
        try:
            db_loader = getattr(self.parser, 'db_loader', None)
            if db_loader:
                gym_db = db_loader.get_gym_database()
                if gym_db:
                    # Keys are normalized names; take a diverse sample
                    keys = list(gym_db.keys())[:120]
                    exercise_sample = [k for k in keys if k and not k.startswith(" ")][:80]
        except Exception:
            pass
        
        focus_instruction = (
            "Focus on suggesting a workout."
            if focus == 'workout' else
            "Focus on suggesting what to eat (given their goals and what they've had today)."
            if focus == 'food' else
            "Suggest both workout and food if relevant; if they're asking about working out, emphasize workout suggestions using their history and the exercise list."
        )
        
        prompt = f"""You are Alfred, a friendly SMS assistant. The user asked for a suggestion.

User message: "{message}"

Their data (use this to personalize):
- Today's food: {today_food_str}
- Recent workouts (last 7 days): {recent_workouts_str}
- Goals: calories {prefs.get('default_calories_goal') or 'not set'}, protein {prefs.get('default_protein_goal') or 'not set'}g

{f"Available exercises (suggest from or similar to these): {', '.join(exercise_sample)}" if exercise_sample else ""}

{focus_instruction}
Keep your reply to 1-3 short sentences, conversational and warm. Mention specific exercises or meal ideas when helpful. Don't list bullets—write like a text message."""

        try:
            out = self.parser.client.generate_content(prompt)
            if not out or not out.strip():
                return self.formatter.format_chitchat()
            if len(out) > 800:
                out = out[:797].rstrip() + "..."
            return out.strip()
        except Exception as e:
            print(f"Error generating suggestion: {e}")
            return self.formatter.format_error("Couldn't generate a suggestion right now.")
    
    def _handle_fact_storage(self, message: str, user_id: int) -> Optional[str]:
        """Handle fact storage"""
        # Simple extraction: "key is value" or "key: value"
        # This is a simplified version - could be enhanced with NLP
        message_lower = message.lower()
        
        # Try to extract key-value pair
        if ' is ' in message_lower:
            parts = message.split(' is ', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
            else:
                return self.formatter.format_error("Use 'key is value' — e.g. 'favorite color is blue'")
        elif ': ' in message:
            parts = message.split(': ', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
            else:
                return self.formatter.format_error("Use 'key: value' — e.g. 'favorite color: blue'")
        else:
            return self.formatter.format_error("Try 'key is value' or 'key: value' so I can save it")
        
        try:
            # Check if fact already exists
            existing = self.fact_repo.get_by_key(user_id, key)
            if existing:
                # Update existing fact
                self.fact_repo.update(existing['id'], {'value': value})
                return f"Got it — updated: {key} = {value}"
            else:
                # Create new fact
                self.fact_repo.create_fact(user_id=user_id, key=key, value=value)
                return f"Got it — saved: {key} = {value}"
                
        except Exception as e:
            print(f"Error saving fact: {e}")
            return self.formatter.format_error("Couldn't save that fact")
    
    def _handle_fact_query(self, message: str, user_id: int) -> Optional[str]:
        """Handle fact queries"""
        # Extract key from message (simple approach)
        # Remove common query words
        query = message.lower()
        query = query.replace('what is', '').replace('what\'s', '').replace('whats', '')
        query = query.replace('where is', '').replace('where\'s', '').replace('wheres', '')
        query = query.replace('who is', '').replace('who\'s', '').replace('whos', '')
        query = query.strip('?').strip()
        
        if not query:
            return self.formatter.format_error("What would you like to know?")
        
        try:
            # Search for facts matching the query
            facts = self.fact_repo.search_facts(user_id, query)
            
            if not facts:
                return f"I don't have anything for '{query}' yet."
            
            # Return first match
            fact = facts[0]
            return f"{fact['key']}: {fact['value']}"
            
        except Exception as e:
            print(f"Error querying fact: {e}")
            return self.formatter.format_error("Couldn't look that up")
