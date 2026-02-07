"""
Water Handler
Handles water logging intents
"""

from typing import Dict, Optional
from datetime import datetime
from supabase import Client

from handlers.base_handler import BaseHandler
from core.context import ConversationContext
from data import WaterRepository


class WaterHandler(BaseHandler):
    """Handles water logging"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.water_repo = WaterRepository(supabase)
    
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle water logging"""
        # Parse water amount (prefer per-user bottle size if available)
        bottle_ml_override = None
        try:
            result = (
                self.supabase.table('users')
                .select('water_bottle_ml')
                .eq('id', user_id)
                .limit(1)
                .execute()
            )
            if result.data:
                bottle_ml_override = result.data[0].get('water_bottle_ml')
        except Exception:
            bottle_ml_override = None

        amount_ml = self.parser.parse_water_amount(message, entities, water_bottle_size_ml=bottle_ml_override)
        
        if not amount_ml or amount_ml <= 0:
            return self.formatter.format_error("I couldn't tell how much. Try 'drank a bottle' or 'drank 500ml'")
        
        # Create water log
        try:
            created = self.water_repo.create_water_log(
                user_id=user_id,
                amount_ml=amount_ml
            )
            
            if not created:
                print(f"Warning: create_water_log returned None/empty for user {user_id}")
                return self.formatter.format_error("Couldn't save that log")
            
            # Invalidate context cache
            context.invalidate_cache()
            
            # Get today's summary
            today_summary = context.get_today_summary()
            
            # Format response
            # Units display (default metric)
            units = 'metric'
            try:
                pref = (
                    self.supabase.table('user_preferences')
                    .select('units')
                    .eq('user_id', user_id)
                    .limit(1)
                    .execute()
                )
                if pref.data and pref.data[0].get('units') in ('metric', 'imperial'):
                    units = pref.data[0]['units']
            except Exception:
                units = 'metric'

            if units == 'imperial':
                oz = amount_ml / 29.5735
                total_oz = today_summary['water']['ml'] / 29.5735
                response = f"Got it — logged {oz:.0f}oz"
                response += f"\nToday: {total_oz:.0f}oz total"
            else:
                liters = amount_ml / 1000
                total_liters = today_summary['water']['liters']
                response = f"Got it — logged {liters:.1f}L"
                response += f"\nToday: {total_liters:.1f}L total"
            
            return response
            
        except Exception as e:
            print(f"Error logging water: {e}")
            return self.formatter.format_error("Couldn't save that water log")
