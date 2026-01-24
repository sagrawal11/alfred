"""
Food Repository
Handles all food log operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from supabase import Client
from .base_repository import BaseRepository


class FoodRepository(BaseRepository):
    """Repository for food logs"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'food_logs')
    
    def create_food_log(self, user_id: int, food_name: str, calories: float,
                        protein: float, carbs: float, fat: float,
                        restaurant: Optional[str] = None,
                        portion_multiplier: float = 1.0) -> Dict[str, Any]:
        """
        Create a new food log entry
        
        Args:
            user_id: User ID
            food_name: Name of the food
            calories: Calories
            protein: Protein in grams
            carbs: Carbs in grams
            fat: Fat in grams
            restaurant: Restaurant name (optional)
            portion_multiplier: Portion multiplier (default: 1.0)
            
        Returns:
            Created food log record
        """
        data = {
            'user_id': user_id,
            'food_name': food_name,
            'calories': float(calories),
            'protein': float(protein),
            'carbs': float(carbs),
            'fat': float(fat),
            'restaurant': restaurant,
            'portion_multiplier': float(portion_multiplier)
        }
        return self.create(data)
    
    def get_by_date(self, user_id: int, date_str: str) -> List[Dict[str, Any]]:
        """
        Get food logs for a specific date
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of food logs for that date
        """
        start = f"{date_str}T00:00:00"
        end = f"{date_str}T23:59:59"
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("timestamp", start)\
            .lte("timestamp", end)\
            .order("timestamp", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def get_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get food logs for a date range
        
        Args:
            user_id: User ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of food logs in the date range
        """
        start = f"{start_date}T00:00:00"
        end = f"{end_date}T23:59:59"
        
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("timestamp", start)\
            .lte("timestamp", end)\
            .order("timestamp", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    def get_by_restaurant(self, user_id: int, restaurant: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get food logs for a specific restaurant
        
        Args:
            user_id: User ID
            restaurant: Restaurant name
            limit: Maximum number of records to return
            
        Returns:
            List of food logs from that restaurant
        """
        query = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("restaurant", restaurant)\
            .order("timestamp", desc=True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    
    def get_today_total(self, user_id: int) -> Dict[str, float]:
        """
        Get today's total calories and macros
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with totals: calories, protein, carbs, fat
        """
        today = datetime.now().date().isoformat()
        logs = self.get_by_date(user_id, today)
        
        totals = {
            'calories': 0.0,
            'protein': 0.0,
            'carbs': 0.0,
            'fat': 0.0
        }
        
        for log in logs:
            multiplier = log.get('portion_multiplier', 1.0)
            totals['calories'] += float(log.get('calories', 0)) * multiplier
            totals['protein'] += float(log.get('protein', 0)) * multiplier
            totals['carbs'] += float(log.get('carbs', 0)) * multiplier
            totals['fat'] += float(log.get('fat', 0)) * multiplier
        
        return totals
