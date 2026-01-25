"""
Query Handler
Handles stats queries, fact storage, and fact queries
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from supabase import Client

from handlers.base_handler import BaseHandler
from core.context import ConversationContext
from data import FactRepository


class QueryHandler(BaseHandler):
    """Handles queries, stats, and facts"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.fact_repo = FactRepository(supabase)
    
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
        
        # Build response based on what user asked for
        response_parts = []
        
        if stats_query.get('all') or stats_query.get('food'):
            food = today_summary['food']
            if food['count'] > 0:
                response_parts.append(f"Food: {food['count']} items, {int(food['calories'])} cal")
        
        if stats_query.get('all') or stats_query.get('water'):
            water = today_summary['water']
            if water['count'] > 0:
                response_parts.append(f"Water: {water['liters']:.1f}L")
        
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
