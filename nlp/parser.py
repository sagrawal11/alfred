"""
Domain-Specific Parser
Parses user messages into structured data for different domains (food, gym, water, etc.)
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dateutil import parser as date_parser

from .llm_types import LLMClient
from .database_loader import DatabaseLoader


class Parser:
    """Parses user messages into structured data"""
    
    def __init__(self, llm_client: LLMClient, database_loader: DatabaseLoader, nutrition_resolver=None):
        """
        Initialize parser
        
        Args:
            llm_client: LLM client instance
            database_loader: DatabaseLoader instance
        """
        self.client = llm_client
        self.db_loader = database_loader
        self.water_bottle_size_ml = database_loader.water_bottle_size_ml
        self.nutrition_resolver = nutrition_resolver
    
    def parse_water_amount(self, message: str, entities: Dict, water_bottle_size_ml: Optional[int] = None) -> Optional[float]:
        """Parse water amount from message"""
        bottle_ml = int(water_bottle_size_ml) if water_bottle_size_ml else int(self.water_bottle_size_ml)
        prompt = f"""Extract the water amount in milliliters (ml) from this message.
Handle these formats:
- "drank a bottle" = {bottle_ml}ml
- "drank 16oz" = 473ml (16 * 29.5735)
- "drank 500ml" = 500ml
- "drank 1 liter" = 1000ml
- "drank half a bottle" = {bottle_ml // 2}ml
- "drank 2 bottles" = {bottle_ml * 2}ml
- "drank 3 bottles" = {bottle_ml * 3}ml

Message: "{message}"

Respond with ONLY the number in ml (just the number, no units), or "null" if no water amount found."""
        
        try:
            text = self.client.generate_content(prompt).lower()
            text = text.strip()
            
            if 'null' in text or 'none' in text or not text:
                return None
            
            # Extract number
            number_match = re.search(r'(\d+\.?\d*)', text)
            if number_match:
                return float(number_match.group(1))
            return None
        except Exception as e:
            print(f"Error parsing water amount: {e}")
            return None
    
    def parse_food(self, message: str) -> Optional[Dict]:
        """Parse food information from message"""
        nicknames_map = self.db_loader.get_restaurant_nicknames()
        nickname_examples = ', '.join([f'"{nickname}" = "{full}"' for nickname, full in list(nicknames_map.items())[:4]])
        
        prompt = f"""Extract food information from this message. Return JSON:
{{
  "food_name": "name of food (extract just the food name, ignore words like 'a', 'an', 'the', 'ate', 'eating')",
  "portion_multiplier": 1.0 (extract portion multiplier: "half" or "half of" = 0.5, "double" = 2.0, "2x" = 2.0, "1.5" = 1.5, "quarter" = 0.25, default = 1.0),
  "restaurant": "restaurant name if mentioned (handle both formats: 'restaurant food' OR 'food from restaurant')",
  "calories": null (extract if mentioned like "200 cal", "200 calories"),
  "protein_g": null (extract if mentioned like "20g protein", "20g p"),
  "carbs_g": null (extract if mentioned like "22g carbs", "22g c"),
  "fat_g": null (extract if mentioned like "6g fat", "6g f"),
  "dietary_fiber_g": null (extract if mentioned like "3g fiber"),
  "sodium_mg": null (extract if mentioned like "200mg sodium"),
  "sugars_g": null (extract if mentioned like "5g sugar")
}}

IMPORTANT RULES:
1. Restaurant can appear in TWO formats:
   - "restaurant food" (most common): "kraft quesadilla", "gsoy brown rice", "skillet omelette", "pitch pizza"
   - "food from restaurant" (less common): "ice cream sundae from gothic", "quesadilla from kraft"
2. Restaurant nickname mappings: {nickname_examples}
3. Portion multipliers - extract from phrases like:
   - "half" or "half of" = 0.5
   - "double" = 2.0
   - "2x" or "2 x" = 2.0
   - "1.5" or "one and a half" = 1.5
   - "quarter" = 0.25
   - Numbers like "2 quesadillas" = 2.0
4. Ignore filler words: "just ate a", "just ate", "eating a", "had a", etc.
5. Food name should be clean: remove articles ("a", "an", "the") and action words ("ate", "eating", "had")
6. If macros are provided in the message, extract them directly. User-provided macros take priority over database values.

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self.client.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                food_data = json.loads(json_match.group())
                
                # Look up in food database (guard against None / non-str)
                raw_food = food_data.get('food_name')
                food_name = (str(raw_food).lower().strip() if raw_food is not None else '') or ''
                raw_rest = food_data.get('restaurant')
                restaurant = (str(raw_rest).lower().strip() if raw_rest is not None else '') or ''
                
                # Normalize restaurant name
                if restaurant:
                    nicknames_map = self.db_loader.get_restaurant_nicknames()
                    normalized_restaurant = nicknames_map.get(restaurant, restaurant)
                    if normalized_restaurant != restaurant:
                        restaurant = normalized_restaurant
                    
                    restaurant_variations = self.db_loader.get_restaurant_variations(restaurant)
                    food_name_spaces = food_name.replace('_', ' ')
                    
                    # Build search terms
                    search_terms = []
                    for restaurant_var in restaurant_variations:
                        search_terms.append(f"{restaurant_var} {food_name}")
                        if food_name_spaces != food_name:
                            search_terms.append(f"{restaurant_var} {food_name_spaces}")
                        search_terms.append(f"{food_name} from {restaurant_var}")
                        if food_name_spaces != food_name:
                            search_terms.append(f"{food_name_spaces} from {restaurant_var}")
                else:
                    search_terms = [food_name, food_name.replace('_', ' ')]
                
                # Look up in database
                food_db = self.db_loader.get_food_database()
                matched_food = None
                
                for search_term in search_terms:
                    st = search_term if search_term is not None else ''
                    search_term_lower = (st.lower().strip() if isinstance(st, str) else '')
                    if search_term_lower and search_term_lower in food_db:
                        matched_food = food_db[search_term_lower]
                        break
                
                # Merge database data with extracted data (extracted data takes priority)
                def safe_str(v):
                    return (str(v).strip() if v is not None else '') or ''

                if matched_food:
                    fn = safe_str(matched_food.get('food_name') or food_name) or 'unknown food'
                    rest = restaurant or safe_str(matched_food.get('restaurant'))
                    result = {
                        'food_name': fn,
                        'calories': food_data.get('calories') or matched_food.get('calories', 0),
                        'protein': food_data.get('protein_g') or matched_food.get('protein', 0),
                        'carbs': food_data.get('carbs_g') or matched_food.get('carbs', 0),
                        'fat': food_data.get('fat_g') or matched_food.get('fat', 0),
                        'restaurant': rest or None,
                        'portion_multiplier': food_data.get('portion_multiplier', 1.0)
                    }
                else:
                    result = {
                        'food_name': food_name or 'unknown food',
                        'calories': food_data.get('calories', 0),
                        'protein': food_data.get('protein_g', 0),
                        'carbs': food_data.get('carbs_g', 0),
                        'fat': food_data.get('fat_g', 0),
                        'restaurant': restaurant or None,
                        'portion_multiplier': food_data.get('portion_multiplier', 1.0)
                    }

                    # External nutrition fallback (only if user didn't explicitly provide macros)
                    user_provided = any(
                        food_data.get(k) is not None
                        for k in ["calories", "protein_g", "carbs_g", "fat_g"]
                    )
                    if not user_provided and self.nutrition_resolver is not None:
                        try:
                            nut = self.nutrition_resolver.resolve(
                                query=result.get("food_name") or food_name,
                                restaurant=restaurant or None,
                            )
                            if nut:
                                # Fill macros if available; do not overwrite if somehow present
                                result.update({k: v for k, v in nut.to_parser_fields().items() if v is not None})
                        except Exception as e:
                            print(f"Nutrition resolver failed: {e}")
                
                return result
            return None
        except Exception as e:
            print(f"Error parsing food: {e}")
            return None
    
    def parse_gym_workout(self, message: str) -> Optional[Dict]:
        """Parse gym workout from message"""
        gym_db = self.db_loader.get_gym_database()
        
        # Build exercise context
        exercise_context = ""
        if gym_db:
            exercise_list = []
            for exercise_key, exercise_data in list(gym_db.items())[:30]:  # Limit to first 30
                exercise_name = exercise_key.replace('_', ' ')
                exercise_list.append(f"- {exercise_name}")
            
            if exercise_list:
                exercise_context = f"\n\nKnown exercises:\n" + "\n".join(exercise_list)
        
        prompt = f"""Extract gym workout information from this message. Return JSON:
{{
  "muscle_group": "chest/back/legs/shoulders/arms/core/cardio/full_body",
  "exercises": [
    {{
      "name": "exercise name",
      "sets": [
        {{
          "weight": 135 (or null if bodyweight/cardio),
          "reps": 5 (or null if not specified),
          "set_number": 1
        }}
      ]
    }}
  ]
}}

IMPORTANT: Handle multiple sets with different weights/reps:
- "35s, 40s, 45s for 10, 8, 6" = 3 sets: 35lbs x10, 40lbs x8, 45lbs x6
- "135x5, 185x3, 225x1" = 3 sets: 135lbs x5, 185lbs x3, 225lbs x1
- "bench 135x10x3" = 3 sets of 135lbs x10 reps (same weight/reps for all sets)
- For dumbbells, "35s" means 35 pounds in each hand
- If only one weight/rep is given but multiple sets mentioned, repeat for all sets

Use the muscle_group field to classify the primary muscle group worked.
For cardio exercises, use "cardio" as the muscle_group.
For exercises without weights (push-ups, pull-ups, planks), set weight to null.
{exercise_context}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self.client.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                workout = json.loads(json_match.group())
                
                # Enhance with gym database
                if 'exercises' in workout and workout['exercises']:
                    for exercise in workout['exercises']:
                        exercise_name = exercise.get('name', '')
                        if exercise_name:
                            # Match exercise to database
                            exercise_lower = exercise_name.lower().strip()
                            if exercise_lower in gym_db:
                                matched = gym_db[exercise_lower]
                                exercise['primary_muscle'] = matched.get('primary_muscle', '')
                                exercise['secondary_muscles'] = matched.get('secondary_muscles', [])
                                exercise['exercise_type'] = matched.get('exercise_type', '')
                                
                                if not workout.get('muscle_group') or workout.get('muscle_group') == 'unknown':
                                    workout['muscle_group'] = matched.get('muscle_group', matched.get('primary_muscle', ''))
                        
                        # Normalize sets format
                        if 'sets' in exercise and isinstance(exercise['sets'], int):
                            sets_count = exercise['sets']
                            weight = exercise.get('weight')
                            reps = exercise.get('reps')
                            exercise['sets'] = [
                                {'weight': weight, 'reps': reps, 'set_number': i+1}
                                for i in range(sets_count)
                            ]
                        elif 'sets' not in exercise or not exercise.get('sets'):
                            weight = exercise.get('weight')
                            reps = exercise.get('reps')
                            if weight or reps:
                                exercise['sets'] = [{'weight': weight, 'reps': reps, 'set_number': 1}]
                
                workout['date'] = datetime.now().isoformat()
                workout['message'] = message
                return workout
            return None
        except Exception as e:
            print(f"Error parsing gym workout: {e}")
            return None
    
    def parse_reminder(self, message: str) -> Optional[Dict]:
        """Parse reminder from message"""
        prompt = f"""Extract reminder information from this message. Return JSON:
{{
  "content": "reminder text",
  "due_date": "YYYY-MM-DD HH:MM:SS" (ISO format, or null if no time specified)
}}

Handle relative times:
- "at 3pm" = today at 3pm
- "tomorrow at 2pm" = tomorrow at 2pm
- "in 1 hour" = current time + 1 hour

Message: "{message}"

Current date/time: {datetime.now().isoformat()}

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self.client.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                reminder = json.loads(json_match.group())
                
                # Parse due_date if it's a string
                if reminder.get('due_date') and isinstance(reminder['due_date'], str):
                    try:
                        reminder['due_date'] = datetime.fromisoformat(reminder['due_date'].replace('Z', '+00:00'))
                    except:
                        reminder['due_date'] = None
                
                reminder['type'] = 'reminder'
                reminder['created_at'] = datetime.now().isoformat()
                return reminder
            return None
        except Exception as e:
            print(f"Error parsing reminder: {e}")
            return None
    
    def parse_assignment(self, message: str) -> Optional[Dict]:
        """Parse assignment from message"""
        prompt = f"""Extract assignment information from this message. Return JSON:
{{
  "class_name": "class name or class number (e.g., 'CS101', 'Math 201', 'History')",
  "assignment_name": "name of the assignment",
  "due_date": "YYYY-MM-DD HH:MM:SS" (ISO format, default to end of day if only date given)
}}

Handle relative dates:
- "due tomorrow" = tomorrow at 11:59 PM
- "due Friday" = this Friday at 11:59 PM (or next Friday if today is after Friday)
- "due March 15" = March 15 at 11:59 PM
- "due next week" = 7 days from now at 11:59 PM

Message: "{message}"

Current date/time: {datetime.now().isoformat()}

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self.client.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                assignment = json.loads(json_match.group())
                
                # Parse due_date
                if assignment.get('due_date') and isinstance(assignment['due_date'], str):
                    try:
                        due_date = datetime.fromisoformat(assignment['due_date'].replace('Z', '+00:00'))
                        if due_date.hour == 0 and due_date.minute == 0 and due_date.second == 0:
                            due_date = due_date.replace(hour=23, minute=59, second=59)
                        assignment['due_date'] = due_date
                    except:
                        assignment['due_date'] = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
                else:
                    assignment['due_date'] = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
                
                assignment['created_at'] = datetime.now().isoformat()
                return assignment
            return None
        except Exception as e:
            print(f"Error parsing assignment: {e}")
            return None
    
    def parse_water_goal(self, message: str) -> Optional[Dict]:
        """Parse water goal from message"""
        prompt = f"""Extract water goal information from this message. Return JSON with:
{{
  "goal_liters": <number in liters (e.g., 5 for "5L" or "5 liters")>,
  "target_date": <date in YYYY-MM-DD format, or "today" or "tomorrow" or null if not specified>
}}

Examples:
- "my water goal for tomorrow is 5L" -> {{"goal_liters": 5, "target_date": "tomorrow"}}
- "set water goal to 3L today" -> {{"goal_liters": 3, "target_date": "today"}}
- "water goal is 4L" -> {{"goal_liters": 4, "target_date": "today"}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self.client.generate_content(prompt)
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                goal_data = json.loads(json_match.group())
                goal_liters = goal_data.get('goal_liters')
                target_date = goal_data.get('target_date', 'today')
                
                if goal_liters:
                    goal_ml = float(goal_liters) * 1000
                    
                    if target_date == 'today':
                        date_str = datetime.now().date().isoformat()
                    elif target_date == 'tomorrow':
                        date_str = (datetime.now() + timedelta(days=1)).date().isoformat()
                    elif target_date:
                        try:
                            date_str = datetime.fromisoformat(target_date).date().isoformat()
                        except:
                            date_str = datetime.now().date().isoformat()
                    else:
                        date_str = datetime.now().date().isoformat()
                    
                    return {
                        'goal_ml': goal_ml,
                        'date': date_str
                    }
            return None
        except Exception as e:
            print(f"Error parsing water goal: {e}")
            return None
    
    def parse_stats_query(self, message: str) -> Dict[str, bool]:
        """Parse what kind of stats the user is asking about"""
        prompt = f"""Determine what stats the user is asking about. Return JSON with:
{{
  "food": true/false (user asking about food/calories/macros),
  "water": true/false (user asking about water intake),
  "gym": true/false (user asking about gym workouts),
  "sleep": true/false (user asking about sleep duration),
  "todos": true/false (user asking about todo list/tasks),
  "reminders": true/false (user asking about reminders/scheduled items),
  "all": true/false (user asking about everything/general stats)
}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self.client.generate_content(prompt)
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                query_data = json.loads(json_match.group())
                return {
                    'food': query_data.get('food', False),
                    'water': query_data.get('water', False),
                    'gym': query_data.get('gym', False),
                    'sleep': query_data.get('sleep', False),
                    'todos': query_data.get('todos', False),
                    'reminders': query_data.get('reminders', False),
                    'all': query_data.get('all', False)
                }
            return {'food': True, 'water': True, 'gym': False, 'sleep': False, 'todos': False, 'reminders': False, 'all': True}
        except Exception as e:
            print(f"Error parsing stats query: {e}")
            return {'food': True, 'water': True, 'gym': False, 'todos': False, 'reminders': False, 'all': True}
    
    def parse_date_query(self, message: str) -> Dict[str, Any]:
        """Parse date/timeframe query from message"""
        current_date = datetime.now().date()
        message_lower = message.lower()
        
        prompt = f"""Extract date or timeframe information from this message. Return JSON with:
{{
  "query_type": "specific_date" or "timeframe" or "none",
  "date_str": "YYYY-MM-DD format date if specific_date (e.g., '2024-01-15'), null otherwise",
  "timeframe_type": "week" or "month" or "day" or null (only if query_type is 'timeframe'),
  "timeframe_count": number like 1, 2, 3 (only if query_type is 'timeframe'),
  "timeframe_direction": "past" or "future" (default: "past")
}}

Current date: {current_date.isoformat()}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self.client.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                query_type = parsed.get('query_type', 'none')
                
                if query_type == 'specific_date':
                    date_str = parsed.get('date_str')
                    if date_str:
                        try:
                            parsed_date = date_parser.parse(date_str).date()
                            return {
                                'type': 'specific_date',
                                'date': parsed_date.isoformat()
                            }
                        except:
                            pass
                
                elif query_type == 'timeframe':
                    timeframe_type = parsed.get('timeframe_type', 'week')
                    count = parsed.get('timeframe_count', 1)
                    direction = parsed.get('timeframe_direction', 'past')
                    
                    if timeframe_type in ['week', 'month', 'day']:
                        return {
                            'type': 'timeframe',
                            'timeframe': timeframe_type,
                            'count': int(count),
                            'direction': direction
                        }
            
            # Fallback to simple patterns
            if 'yesterday' in message_lower:
                yesterday = (current_date - timedelta(days=1)).isoformat()
                return {'type': 'specific_date', 'date': yesterday}
            elif 'today' in message_lower:
                return {'type': 'specific_date', 'date': current_date.isoformat()}
            elif 'last week' in message_lower or 'past week' in message_lower:
                return {'type': 'timeframe', 'timeframe': 'week', 'count': 1, 'direction': 'past'}
            elif 'last month' in message_lower or 'past month' in message_lower:
                return {'type': 'timeframe', 'timeframe': 'month', 'count': 1, 'direction': 'past'}
            
            return {'type': None}
        except Exception as e:
            print(f"Error parsing date query: {e}")
            return {'type': None}
    
    def parse_food_suggestion(self, message: str) -> Dict:
        """Parse food suggestion query to extract constraints"""
        prompt = f"""Extract food constraints from this message. Return JSON with:
{{
  "high_protein": true/false,
  "low_protein": true/false,
  "high_calories": true/false,
  "low_calories": true/false,
  "high_carbs": true/false,
  "low_carbs": true/false,
  "high_fat": true/false,
  "low_fat": true/false,
  "restaurant": "restaurant_name" or null,
  "location": "location_name" or null
}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self.client.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                constraints = json.loads(json_match.group())
                return {
                    'high_protein': constraints.get('high_protein', False),
                    'low_protein': constraints.get('low_protein', False),
                    'high_calories': constraints.get('high_calories', False),
                    'low_calories': constraints.get('low_calories', False),
                    'high_carbs': constraints.get('high_carbs', False),
                    'low_carbs': constraints.get('low_carbs', False),
                    'high_fat': constraints.get('high_fat', False),
                    'low_fat': constraints.get('low_fat', False),
                    'restaurant': constraints.get('restaurant'),
                    'location': constraints.get('location')
                }
            return {}
        except Exception as e:
            print(f"Error parsing food suggestion: {e}")
            return {}
    
    def parse_portion_multiplier(self, message: str) -> float:
        """Parse portion multiplier from message"""
        prompt = f"""Extract portion multiplier from this message:
- "half" or "half of" = 0.5
- "double" = 2.0
- "2x" or "2 x" = 2.0
- "1.5" or "one and a half" = 1.5
- "quarter" = 0.25
- Numbers like "2 quesadillas" = 2.0
- Default = 1.0

Message: "{message}"

Respond with ONLY the number (just the number, no text), or "1.0" if not found."""
        
        try:
            text = self.client.generate_content(prompt).lower()
            number_match = re.search(r'(\d+\.?\d*)', text)
            if number_match:
                return float(number_match.group(1))
            return 1.0
        except Exception as e:
            print(f"Error parsing portion multiplier: {e}")
            return 1.0
