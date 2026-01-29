"""
Entity Extractor
Extracts structured entities from user messages
"""

import json
import re
from typing import Dict
from .llm_types import LLMClient


class EntityExtractor:
    """Extracts entities (people, times, dates, numbers, etc.) from messages"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize entity extractor
        
        Args:
            llm_client: LLM client instance
        """
        self.client = llm_client
    
    def extract(self, message: str) -> Dict:
        """
        Extract entities from message
        
        Args:
            message: User message
            
        Returns:
            Dictionary with extracted entities:
            {
                "people": [...],
                "times": [...],
                "dates": [...],
                "numbers": [...],
                "locations": [...],
                "food_items": [...],
                "exercises": [...]
            }
        """
        prompt = f"""Extract structured information from this SMS message. Return JSON with:
{{
  "people": [list of people mentioned],
  "times": [list of times mentioned],
  "dates": [list of dates mentioned],
  "numbers": [list of numbers mentioned],
  "locations": [list of locations mentioned],
  "food_items": [list of food items mentioned],
  "exercises": [list of exercises mentioned]
}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self.client.generate_content(prompt)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(text)
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return {
                'people': [], 'times': [], 'dates': [], 'numbers': [],
                'locations': [], 'food_items': [], 'exercises': []
            }
