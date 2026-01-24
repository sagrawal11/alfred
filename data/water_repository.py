"""
Water Repository
Handles all water log operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from supabase import Client
from .base_repository import BaseRepository


class WaterRepository(BaseRepository):
    """Repository for water logs"""
    
    def __init__(self, supabase_client: Client):
        super().__init__(supabase_client, 'water_logs')
    
    def create_water_log(self, user_id: int, amount_ml: float, 
                        amount_oz: Optional[float] = None) -> Dict[str, Any]:
        """
        Create a new water log entry
        
        Args:
            user_id: User ID
            amount_ml: Amount in milliliters
            amount_oz: Amount in ounces (auto-calculated if not provided)
            
        Returns:
            Created water log record
        """
        if amount_oz is None:
            amount_oz = amount_ml / 29.5735
        
        data = {
            'user_id': user_id,
            'amount_ml': float(amount_ml),
            'amount_oz': float(amount_oz)
        }
        return self.create(data)
    
    def get_by_date(self, user_id: int, date_str: str) -> List[Dict[str, Any]]:
        """
        Get water logs for a specific date
        
        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of water logs for that date
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
    
    def get_today_total(self, user_id: int) -> float:
        """
        Get today's total water intake in ml
        
        Args:
            user_id: User ID
            
        Returns:
            Total water intake in milliliters
        """
        today = datetime.now().date().isoformat()
        logs = self.get_by_date(user_id, today)
        
        total = sum(float(log.get('amount_ml', 0)) for log in logs)
        return total
    
    def get_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get water logs for a date range
        
        Args:
            user_id: User ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of water logs in the date range
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
