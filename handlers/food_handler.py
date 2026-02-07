"""
Food Handler
Handles food logging intents
"""

from datetime import datetime
from typing import Dict, Optional

from supabase import Client

from core.context import ConversationContext
from data import FoodLogMetadataRepository, FoodRepository
from handlers.base_handler import BaseHandler


class FoodHandler(BaseHandler):
    """Handles food logging"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.food_repo = FoodRepository(supabase)
        self.food_meta_repo = FoodLogMetadataRepository(supabase)
    
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle food logging"""
        # Parse food from message
        food_data = self.parser.parse_food(message)
        
        if not food_data:
            return self.formatter.format_error("I couldn't make out the food. Try something like 'ate a quesadilla'")
        
        # Create food log (handle None values)
        def safe_float(value, default=0.0):
            """Safely convert value to float, handling None"""
            if value is None:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        food_log = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'food_name': food_data.get('food_name', '') or 'unknown food',
            'calories': safe_float(food_data.get('calories'), 0),
            'protein': safe_float(food_data.get('protein'), 0),
            'carbs': safe_float(food_data.get('carbs'), 0),
            'fat': safe_float(food_data.get('fat'), 0),
            'restaurant': food_data.get('restaurant'),
            'portion_multiplier': safe_float(food_data.get('portion_multiplier'), 1.0)
        }
        
        # Save to database
        try:
            created = self.food_repo.create_food_log(
                user_id=user_id,
                food_name=food_log['food_name'],
                calories=food_log['calories'],
                protein=food_log['protein'],
                carbs=food_log['carbs'],
                fat=food_log['fat'],
                restaurant=food_log.get('restaurant'),
                portion_multiplier=food_log['portion_multiplier']
            )
            
            if not created:
                print(f"Warning: create_food_log returned None/empty for user {user_id}")
                return self.formatter.format_error("Couldn't save that log")

            # Persist nutrition metadata when available (non-blocking)
            try:
                src = food_data.get("nutrition_source")
                if src:
                    self.food_meta_repo.create_metadata(
                        food_log_id=int(created.get("id")),
                        source=str(src),
                        confidence=float(food_data.get("nutrition_confidence") or 0.5),
                        basis=food_data.get("nutrition_basis"),
                        serving_weight_grams=food_data.get("serving_weight_grams"),
                        resolved_name=food_data.get("resolved_name"),
                        raw_query=message,
                        raw=food_data.get("nutrition_raw"),
                    )
            except Exception as e:
                print(f"Warning: failed to persist food metadata: {e}")
            
            # Invalidate context cache
            context.invalidate_cache()
            
            # Get today's summary
            today_summary = context.get_today_summary()
            
            # Format response
            food_name = food_log['food_name']
            if food_log.get('restaurant'):
                food_name = f"{food_log['restaurant']} {food_name}"
            
            calories = food_log['calories'] * food_log['portion_multiplier']
            
            response = f"Got it — logged {food_name}"
            if calories > 0:
                response += f" ({int(calories)} cal)"
            
            # Add today's totals
            if today_summary['food']['count'] > 0:
                total_cal = today_summary['food']['calories']
                response += f"\nToday: {int(total_cal)} cal"
            
            return response
            
        except Exception as e:
            print(f"Error logging food: {e}")
            return self.formatter.format_error("Couldn't save that food log")
