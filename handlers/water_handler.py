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
        # Parse water amount
        amount_ml = self.parser.parse_water_amount(message, entities)
        
        if not amount_ml or amount_ml <= 0:
            return self.formatter.format_error("Couldn't parse water amount. Try: 'drank a bottle' or 'drank 500ml'")
        
        # Create water log
        try:
            created = self.water_repo.create_water_log(
                user_id=user_id,
                amount_ml=amount_ml
            )
            
            if not created:
                print(f"Warning: create_water_log returned None/empty for user {user_id}")
                return self.formatter.format_error("Failed to save water log")
            
            # Invalidate context cache
            context.invalidate_cache()
            
            # Get today's summary
            today_summary = context.get_today_summary()
            
            # Format response
            liters = amount_ml / 1000
            total_liters = today_summary['water']['liters']
            
            response = f"✓ Logged {liters:.1f}L"
            response += f"\nToday: {total_liters:.1f}L total"
            
            return response
            
        except Exception as e:
            print(f"Error logging water: {e}")
            return self.formatter.format_error("Error saving water log")
