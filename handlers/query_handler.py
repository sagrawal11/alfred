"""
Query Handler
Handles stats queries, fact storage, and fact queries
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from supabase import Client

from handlers.base_handler import BaseHandler
from core.context import ConversationContext
from data import FactRepository
from data import UserPreferencesRepository


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
            return "No data for today yet. Start logging!"
        
        return "\n".join(response_parts)
    
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
                return self.formatter.format_error("Format: 'key is value'")
        elif ': ' in message:
            parts = message.split(': ', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
            else:
                return self.formatter.format_error("Format: 'key: value'")
        else:
            return self.formatter.format_error("Format: 'key is value' or 'key: value'")
        
        try:
            # Check if fact already exists
            existing = self.fact_repo.get_by_key(user_id, key)
            if existing:
                # Update existing fact
                self.fact_repo.update(existing['id'], {'value': value})
                return f"✓ Updated: {key} = {value}"
            else:
                # Create new fact
                self.fact_repo.create_fact(user_id=user_id, key=key, value=value)
                return f"✓ Saved: {key} = {value}"
                
        except Exception as e:
            print(f"Error saving fact: {e}")
            return self.formatter.format_error("Error saving fact")
    
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
            return self.formatter.format_error("What do you want to know?")
        
        try:
            # Search for facts matching the query
            facts = self.fact_repo.search_facts(user_id, query)
            
            if not facts:
                return f"Couldn't find '{query}'"
            
            # Return first match
            fact = facts[0]
            return f"{fact['key']}: {fact['value']}"
            
        except Exception as e:
            print(f"Error querying fact: {e}")
            return self.formatter.format_error("Error searching facts")
