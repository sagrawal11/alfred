#!/usr/bin/env python3
"""
Gemini NLP Processor using Google Gemini API
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Try new SDK first, fallback to old one
try:
    from google import genai as google_genai
    NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    NEW_SDK = False

class GeminiNLPProcessor:
    def __init__(self, food_db=None, model_name=None):
        """Initialize the Gemini NLP processor
        
        Args:
            food_db: Food database dictionary
            model_name: Model to use (defaults to GEMINI_MODEL env var or 'gemini-2.5-flash')
                       Gemini models: 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite'
                       Gemma models: 'gemma-3-1b-it', 'gemma-3-4b-it', 'gemma-3-12b-it', 'gemma-3-27b-it'
                       Note: Different models have separate quota limits!
        """
        print("🧠 Initializing Gemini NLP Processor...")
        
        # Get API key from config
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Get model name from parameter, env var, or default
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        
        # Configure Gemini - use new SDK if available
        if NEW_SDK:
            self.client = google_genai.Client(api_key=api_key)
            print(f"✅ Gemini client loaded (new SDK - {self.model_name})")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"✅ Gemini model loaded (old SDK - {self.model_name})")
        
        # Rate limiting: Different models have different quotas
        # Gemma models: 30 requests/min, 14.4k requests/day
        # Gemini models: 5 requests/min, 20 requests/day (free tier)
        self.last_request_time = 0
        if 'gemma' in self.model_name.lower():
            # Gemma: 30 requests per minute = 2 seconds between requests
            self.min_request_interval = 2
            print(f"⚡ Using Gemma rate limits: 30 req/min, 14.4k req/day")
        else:
            # Gemini free tier: 5 requests per minute = 12 seconds between requests
            self.min_request_interval = 12
            print(f"⚡ Using Gemini rate limits: 5 req/min, 20 req/day (free tier)")
        
        # Load food database and flatten nested structure
        raw_food_db = food_db or self._load_food_database()
        
        # Load snacks database and merge with food database
        raw_snacks_db = self._load_snacks_database()
        if raw_snacks_db:
            # Merge snacks into food database (snacks are treated as a "restaurant" category)
            raw_food_db = {**raw_food_db, **raw_snacks_db}
        
        self.food_db = self._flatten_food_database(raw_food_db)
        
        # Load gym workout database
        self.gym_db = self._load_gym_database()
        
        # Get water bottle size from config
        from config import Config
        self.water_bottle_size_ml = Config.WATER_BOTTLE_SIZE_ML
        
        # System prompt for the model
        self.system_prompt = """You are an intelligent SMS assistant that helps users log:
- Water intake (amounts in oz, ml, bottles, liters)
- Food items (with portion sizes)
- Gym workouts (exercise, weight, reps, sets)
- Reminders (with time and content)
- Todos (simple task lists)

Extract structured information from user messages. Be accurate and handle variations in phrasing."""
        
        print("🧠 Gemini NLP Processor ready!")
    
    def _rate_limit(self):
        """Enforce rate limiting for free tier (5 requests per minute)"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            print(f"⏳ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _generate_content(self, prompt: str, is_retry: bool = False) -> str:
        """Generate content with rate limiting and error handling"""
        if not is_retry:
            self._rate_limit()
        
        try:
            if NEW_SDK:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            else:
                response = self.model.generate_content(prompt)
                return self._get_response_text(response)
        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error and we haven't retried yet
            if not is_retry and ("429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower()):
                # Extract retry delay if available
                retry_match = re.search(r'retry in (\d+)', error_str)
                if retry_match:
                    retry_seconds = int(retry_match.group(1)) + 1
                    print(f"⏳ Rate limited. Waiting {retry_seconds}s before retry...")
                    time.sleep(retry_seconds)
                    # Update last request time to account for the wait
                    self.last_request_time = time.time()
                    # Retry once (skip rate limit on retry)
                    return self._generate_content(prompt, is_retry=True)
            raise
    
    def _get_response_text(self, response) -> str:
        """Extract text from Gemini response, handling different response formats"""
        if hasattr(response, 'text'):
            return response.text.strip()
        elif hasattr(response, 'parts') and response.parts:
            return response.parts[0].text.strip()
        elif hasattr(response, 'candidates') and response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
        return ""
    
    def _load_food_database(self):
        """Load custom food database from file"""
        try:
            from config import Config
            with open(Config.FOOD_DATABASE_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  Custom food database not found, using empty DB")
            return {}
    
    def _load_snacks_database(self):
        """Load snacks database from file"""
        try:
            from config import Config
            with open(Config.SNACKS_DATABASE_PATH, 'r') as f:
                snacks_db = json.load(f)
                print("✅ Snacks database loaded")
                return snacks_db
        except FileNotFoundError:
            print("⚠️  Snacks database not found, skipping")
            return {}
    
    def _flatten_food_database(self, raw_db):
        """Flatten nested food database structure into a flat dict for easier lookup
        
        Input: {"sazon": {"quesedilla": {...}, "burrito": {...}}, "krafthouse": {"quesedilla": {...}}}
        Output: {"quesedilla": {...}, "sazon quesedilla": {...}, "krafthouse quesedilla": {...}}
        
        Note: Restaurant name is now the top-level key, not a field in food_data
        """
        flattened = {}
        if not raw_db:
            return flattened
        
        for restaurant, foods in raw_db.items():
            if isinstance(foods, dict):
                for food_key, food_data in foods.items():
                    # Add restaurant name to food data for later reference
                    food_data_with_restaurant = {**food_data, 'restaurant': restaurant}
                    
                    # Add food with just its key (for generic matching)
                    # If multiple restaurants have same food, last one wins (could be improved)
                    flattened[food_key] = food_data_with_restaurant
                    
                    # Add "restaurant food" format (e.g., "sazon quesedilla")
                    flattened[f"{restaurant} {food_key}"] = food_data_with_restaurant
                    
                    # Add "food restaurant" format (e.g., "quesedilla sazon")
                    flattened[f"{food_key} {restaurant}"] = food_data_with_restaurant
                    
                    # Handle common misspellings/variations
                    if food_key.lower() in ['quesadilla', 'quesedilla']:
                        # Add variations for both spellings
                        for spelling in ['quesadilla', 'quesedilla']:
                            flattened[f"{restaurant} {spelling}"] = food_data_with_restaurant
                            flattened[f"{spelling} {restaurant}"] = food_data_with_restaurant
        
        return flattened
    
    def _load_gym_database(self):
        """Load gym workout database from file"""
        try:
            from config import Config
            with open(Config.GYM_DATABASE_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  Gym workout database not found, using empty DB")
            return {}
    
    def _flatten_gym_database(self, raw_db):
        """Flatten nested gym database structure into a flat dict for easier lookup
        
        Input: {"chest": {"bench_press": {...}}, "back": {"deadlift": {...}}}
        Output: {"bench press": {...}, "bench_press": {...}, "chest bench press": {...}}
        """
        flattened = {}
        if not raw_db:
            return flattened
        
        for muscle_group, exercises in raw_db.items():
            if isinstance(exercises, dict):
                for exercise_key, exercise_data in exercises.items():
                    # Add muscle group to exercise data
                    exercise_data_with_muscle = {**exercise_data, 'muscle_group': muscle_group}
                    
                    # Add exercise with its key (e.g., "bench_press")
                    flattened[exercise_key] = exercise_data_with_muscle
                    
                    # Add exercise with underscores replaced by spaces (e.g., "bench press")
                    exercise_name = exercise_key.replace('_', ' ')
                    flattened[exercise_name] = exercise_data_with_muscle
                    
                    # Add all common variations
                    if 'common_variations' in exercise_data:
                        for variation in exercise_data['common_variations']:
                            flattened[variation.lower()] = exercise_data_with_muscle
                    
                    # Add "muscle_group exercise" format (e.g., "chest bench press")
                    flattened[f"{muscle_group} {exercise_name}"] = exercise_data_with_muscle
                    flattened[f"{muscle_group} {exercise_key}"] = exercise_data_with_muscle
        
        return flattened
    
    def _match_exercise(self, exercise_name: str) -> Optional[Dict]:
        """Match an exercise name to the gym database"""
        if not self.gym_db:
            return None
        
        # Flatten database for lookup
        flattened = self._flatten_gym_database(self.gym_db)
        
        # Try exact match first
        exercise_lower = exercise_name.lower().strip()
        if exercise_lower in flattened:
            return flattened[exercise_lower]
        
        # Try partial match (check if exercise name contains any database key)
        for key, exercise_data in flattened.items():
            if key in exercise_lower or exercise_lower in key:
                return exercise_data
        
        return None
    
    def classify_intent(self, message: str) -> str:
        """Classify the intent of a message using Gemini"""
        prompt = f"""Classify this SMS message into one of these intents:
- water_logging: User is logging water intake
- food_logging: User is logging food consumption
- gym_workout: User is logging a gym workout/exercise
- reminder_set: User wants to set a reminder (if message contains a time/date like "at 5pm", "tomorrow", "in 1 hour", etc., classify as reminder_set even if it also sounds like a todo)
- todo_add: User wants to add a todo item (only if there's NO specific time/date mentioned)
- water_goal_set: User wants to set a custom water goal for a specific day (e.g., "my water goal for tomorrow is 5L", "set water goal to 3L today")
- stats_query: User is asking about their stats/totals (e.g., "how much have I eaten", "how much water have I drank", "what's my total for today", "show me my stats")
- task_complete: User is marking a task/reminder as complete (e.g., "called mom", "did groceries", "finished homework", "done with that", "completed the task")
- vague_completion: User is indicating completion but message is vague/ambiguous (e.g., "just finished", "done", "finished", "all done", "complete" without specific details)
- what_should_i_do: User is asking what they should do now (e.g., "what should I do now", "what's next", "what do I do", "suggest something")
- undo_edit: User wants to undo or edit a previous action (e.g., "undo last", "delete last food", "edit last water", "remove last reminder", "undo that")
- confirmation: User is confirming or denying something (e.g., "yes", "yep", "correct", "no", "nope", "that's right")
- unknown: Doesn't match any category

IMPORTANT: If a message has BOTH a task/todo AND a time/date (e.g., "I need to call mama at 5pm tomorrow"), classify it as "reminder_set" because reminders are more specific than todos.

Message: "{message}"

Respond with ONLY the intent name, nothing else."""
        
        try:
            intent = self._generate_content(prompt).lower()
            
            # Validate intent
            valid_intents = ['water_logging', 'food_logging', 'gym_workout', 'reminder_set', 'todo_add', 'water_goal_set', 'stats_query', 'task_complete', 'vague_completion', 'what_should_i_do', 'undo_edit', 'confirmation', 'unknown']
            if intent in valid_intents:
                return intent
            else:
                # Try to extract intent from response
                for valid_intent in valid_intents:
                    if valid_intent in intent:
                        return valid_intent
                return 'unknown'
        except Exception as e:
            print(f"❌ Error classifying intent: {e}")
            return 'unknown'
    
    def extract_entities(self, message: str) -> Dict:
        """Extract entities from message using Gemini"""
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
            text = self._generate_content(prompt)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(text)
        except Exception as e:
            print(f"❌ Error extracting entities: {e}")
            return {
                'people': [], 'times': [], 'dates': [], 'numbers': [],
                'locations': [], 'food_items': [], 'exercises': []
            }
    
    def parse_water_amount(self, message: str, entities: Dict) -> Optional[float]:
        """Parse water amount from message"""
        bottle_size = self.water_bottle_size_ml
        prompt = f"""Extract the water amount in milliliters (ml) from this message.
Handle these formats:
- "drank a bottle" = {bottle_size}ml
- "drank 16oz" = 473ml (16 * 29.5735)
- "drank 500ml" = 500ml
- "drank 1 liter" = 1000ml
- "drank half a bottle" = {bottle_size // 2}ml
- "drank 2 bottles" = {bottle_size * 2}ml
- "drank 3 bottles" = {bottle_size * 3}ml

Message: "{message}"

Respond with ONLY the number in ml (just the number, no units), or "null" if no water amount found."""
        
        try:
            text = self._generate_content(prompt).lower()
            
            # Extract number
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                return float(numbers[0])
            return None
        except Exception as e:
            print(f"❌ Error parsing water amount: {e}")
            return None
    
    def parse_food(self, message: str) -> Optional[Dict]:
        """Parse food information from message, extracting macros if provided"""
        prompt = f"""Extract food information from this message. Return JSON:
{{
  "food_name": "name of food",
  "portion_multiplier": 1.0,
  "restaurant": "restaurant name if mentioned",
  "calories": null (extract if mentioned like "200 cal", "200 calories"),
  "protein_g": null (extract if mentioned like "20g protein", "20g p"),
  "carbs_g": null (extract if mentioned like "22g carbs", "22g c"),
  "fat_g": null (extract if mentioned like "6g fat", "6g f"),
  "dietary_fiber_g": null (extract if mentioned like "3g fiber"),
  "sodium_mg": null (extract if mentioned like "200mg sodium"),
  "sugars_g": null (extract if mentioned like "5g sugar")
}}

IMPORTANT: If macros are provided in the message (calories, protein, carbs, fat, etc.), extract them directly.
If the food is in this database, you can use its nutrition info, but user-provided macros take priority:
{json.dumps(list(self.food_db.keys())[:10], indent=2)}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self._generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                food_data = json.loads(json_match.group())
                
                # Look up in food database (now flattened)
                food_name = food_data.get('food_name', '').lower()
                restaurant = food_data.get('restaurant', '').lower()
                
                # Try exact match first (e.g., "sazon quesadilla")
                search_terms = [food_name]
                if restaurant:
                    search_terms.append(f"{restaurant} {food_name}")
                    search_terms.append(f"{food_name} {restaurant}")
                
                # Look for best match
                best_match = None
                best_score = 0
                
                for key, value in self.food_db.items():
                    key_lower = key.lower()
                    # Check if any search term matches
                    for term in search_terms:
                        if term in key_lower or key_lower in term:
                            # Score based on match quality
                            if term == key_lower:
                                score = 100  # Exact match
                            elif term in key_lower:
                                score = 50   # Partial match
                            else:
                                score = 25   # Contains match
                            
                            if score > best_score:
                                best_score = score
                                best_match = (key, value)
                
                # Check if macros were provided in the message
                calories = food_data.get('calories')
                protein_g = food_data.get('protein_g')
                carbs_g = food_data.get('carbs_g')
                fat_g = food_data.get('fat_g')
                dietary_fiber_g = food_data.get('dietary_fiber_g')
                sodium_mg = food_data.get('sodium_mg')
                sugars_g = food_data.get('sugars_g')
                
                has_provided_macros = any([calories, protein_g, carbs_g, fat_g])
                
                if best_match:
                    key, value = best_match
                    # Extract food name from key (remove restaurant prefix if present)
                    food_name = key.replace('_', ' ')
                    # Remove restaurant prefix if it exists (e.g., "sazon quesedilla" -> "quesedilla")
                    matched_restaurant = value.get('restaurant', '')
                    if matched_restaurant and food_name.startswith(matched_restaurant + ' '):
                        food_name = food_name[len(matched_restaurant) + 1:]
                    elif matched_restaurant and food_name.endswith(' ' + matched_restaurant):
                        food_name = food_name[:-len(matched_restaurant) - 1]
                    
                    # Use provided macros if available, otherwise use database values
                    if has_provided_macros:
                        food_data_dict = {
                            'calories': calories if calories is not None else value.get('calories', 0),
                            'protein': protein_g if protein_g is not None else value.get('protein_g', value.get('protein', 0)),
                            'carbs': carbs_g if carbs_g is not None else value.get('carbs_g', value.get('carbs', 0)),
                            'fat': fat_g if fat_g is not None else value.get('fat_g', value.get('fat', 0)),
                            'fiber': dietary_fiber_g if dietary_fiber_g is not None else value.get('dietary_fiber_g', value.get('fiber', 0))
                        }
                    else:
                        food_data_dict = value
                    
                    return {
                        'food_name': food_name,
                        'food_data': food_data_dict,
                        'portion_multiplier': food_data.get('portion_multiplier', 1.0),
                        'restaurant': matched_restaurant
                    }
                
                # If not found in database but macros provided, use those
                if has_provided_macros:
                    return {
                        'food_name': food_data.get('food_name', ''),
                        'food_data': {
                            'calories': calories if calories is not None else 0,
                            'protein': protein_g if protein_g is not None else 0,
                            'carbs': carbs_g if carbs_g is not None else 0,
                            'fat': fat_g if fat_g is not None else 0,
                            'fiber': dietary_fiber_g if dietary_fiber_g is not None else 0
                        },
                        'portion_multiplier': food_data.get('portion_multiplier', 1.0),
                        'restaurant': food_data.get('restaurant')
                    }
                
                # If not found and no macros provided, return basic structure (will log as unknown)
                return {
                    'food_name': food_data.get('food_name', ''),
                    'food_data': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0},
                    'portion_multiplier': food_data.get('portion_multiplier', 1.0),
                    'restaurant': food_data.get('restaurant')
                }
            return None
        except Exception as e:
            print(f"❌ Error parsing food: {e}")
            return None
    
    def parse_gym_workout(self, message: str) -> Optional[Dict]:
        """Parse gym workout from message using gym database for better classification"""
        # Build exercise list from database for context
        exercise_context = ""
        if self.gym_db:
            exercise_list = []
            for muscle_group, exercises in self.gym_db.items():
                for exercise_key, exercise_data in exercises.items():
                    exercise_name = exercise_key.replace('_', ' ')
                    variations = exercise_data.get('common_variations', [])
                    exercise_list.append(f"- {exercise_name} ({muscle_group}): {', '.join(variations[:3])}")
            
            if exercise_list:
                exercise_context = f"\n\nKnown exercises:\n" + "\n".join(exercise_list[:30])  # Limit to first 30 for context
        
        prompt = f"""Extract gym workout information from this message. Return JSON:
{{
  "muscle_group": "chest/back/legs/shoulders/arms/core/cardio/full_body",
  "exercises": [
    {{
      "name": "exercise name",
      "weight": 135 (or null if bodyweight/cardio),
      "reps": 5 (or null if not specified),
      "sets": 1 (or null if not specified)
    }}
  ]
}}

Use the muscle_group field to classify the primary muscle group worked.
For cardio exercises, use "cardio" as the muscle_group.
For exercises without weights (push-ups, pull-ups, planks), set weight to null.
{exercise_context}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self._generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                workout = json.loads(json_match.group())
                
                # Enhance workout data with gym database information
                if 'exercises' in workout and workout['exercises']:
                    for exercise in workout['exercises']:
                        exercise_name = exercise.get('name', '')
                        if exercise_name:
                            # Try to match exercise to database
                            matched_exercise = self._match_exercise(exercise_name)
                            if matched_exercise:
                                # Add database information to exercise
                                exercise['primary_muscle'] = matched_exercise.get('primary_muscle', '')
                                exercise['secondary_muscles'] = matched_exercise.get('secondary_muscles', [])
                                exercise['exercise_type'] = matched_exercise.get('exercise_type', '')
                                
                                # If muscle_group wasn't correctly identified, use database
                                if not workout.get('muscle_group') or workout.get('muscle_group') == 'unknown':
                                    workout['muscle_group'] = matched_exercise.get('muscle_group', matched_exercise.get('primary_muscle', ''))
                
                workout['date'] = datetime.now().isoformat()
                workout['message'] = message
                return workout
            return None
        except Exception as e:
            print(f"❌ Error parsing gym workout: {e}")
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
            text = self._generate_content(prompt)
            
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
            print(f"❌ Error parsing reminder: {e}")
            return None
    
    def parse_water_goal(self, message: str) -> Optional[Dict]:
        """Parse water goal from message (amount and target date)"""
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
            response_text = self._generate_content(prompt)
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                goal_data = json.loads(json_match.group())
                goal_liters = goal_data.get('goal_liters')
                target_date = goal_data.get('target_date', 'today')
                
                if goal_liters:
                    # Convert liters to milliliters
                    goal_ml = float(goal_liters) * 1000
                    
                    # Parse target date
                    if target_date == 'today':
                        date_str = datetime.now().date().isoformat()
                    elif target_date == 'tomorrow':
                        date_str = (datetime.now() + timedelta(days=1)).date().isoformat()
                    elif target_date:
                        # Try to parse as date string
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
            print(f"❌ Error parsing water goal: {e}")
            return None
    
    def parse_stats_query(self, message: str) -> Dict[str, bool]:
        """Parse what kind of stats the user is asking about"""
        prompt = f"""Determine what stats the user is asking about. Return JSON with:
{{
  "food": true/false (user asking about food/calories/macros),
  "water": true/false (user asking about water intake),
  "gym": true/false (user asking about gym workouts),
  "todos": true/false (user asking about todo list/tasks),
  "reminders": true/false (user asking about reminders/scheduled items),
  "all": true/false (user asking about everything/general stats)
}}

Examples:
- "how much have I eaten" -> {{"food": true, "water": false, "gym": false, "todos": false, "reminders": false, "all": false}}
- "how much water have I drank" -> {{"food": false, "water": true, "gym": false, "todos": false, "reminders": false, "all": false}}
- "what's on my to do list" -> {{"food": false, "water": false, "gym": false, "todos": true, "reminders": false, "all": false}}
- "do I have any reminders" -> {{"food": false, "water": false, "gym": false, "todos": false, "reminders": true, "all": false}}
- "what's my total for today" -> {{"food": true, "water": true, "gym": false, "todos": false, "reminders": false, "all": true}}
- "show me my stats" -> {{"food": true, "water": true, "gym": true, "todos": false, "reminders": false, "all": true}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self._generate_content(prompt)
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                query_data = json.loads(json_match.group())
                return {
                    'food': query_data.get('food', False),
                    'water': query_data.get('water', False),
                    'gym': query_data.get('gym', False),
                    'todos': query_data.get('todos', False),
                    'reminders': query_data.get('reminders', False),
                    'all': query_data.get('all', False)
                }
            # Default: if unclear, show all
            return {'food': True, 'water': True, 'gym': False, 'todos': False, 'reminders': False, 'all': True}
        except Exception as e:
            print(f"❌ Error parsing stats query: {e}")
            # Default: if error, show all
            return {'food': True, 'water': True, 'gym': False, 'todos': False, 'reminders': False, 'all': True}
    
    def guess_intent(self, message: str) -> Optional[Dict]:
        """Try to guess the intent when classification is unclear"""
        prompt = f"""This message was classified as "unknown" but we want to make an educated guess. 
Analyze the message and determine:
1. What is the most likely intent?
2. How confident are you (0.0 to 1.0)?
3. Why do you think this is the intent?

Return JSON with:
{{
  "intent": "<most likely intent name>",
  "confidence": <number between 0.0 and 1.0>,
  "reason": "<brief explanation of why you think this is the intent>"
}}

Available intents: water_logging, food_logging, gym_workout, reminder_set, todo_add, water_goal_set, stats_query, task_complete

If you're not confident (confidence < 0.5), return null or set confidence to 0.

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self._generate_content(prompt)
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                guess_data = json.loads(json_match.group())
                intent = guess_data.get('intent', '').lower()
                confidence = guess_data.get('confidence', 0)
                
                # Validate intent
                valid_intents = ['water_logging', 'food_logging', 'gym_workout', 'reminder_set', 
                               'todo_add', 'water_goal_set', 'stats_query', 'task_complete']
                
                if intent in valid_intents and confidence > 0:
                    return {
                        'intent': intent,
                        'confidence': float(confidence),
                        'reason': guess_data.get('reason', f'This looks like {intent.replace("_", " ")}')
                    }
            return None
        except Exception as e:
            print(f"❌ Error guessing intent: {e}")
            return None
    
    def parse_portion_multiplier(self, message: str) -> float:
        """Parse portion multiplier from message"""
        prompt = f"""Extract portion multiplier from this message:
- "half" = 0.5
- "double" = 2.0
- "2x" = 2.0
- "1.5" = 1.5
- default = 1.0

Message: "{message}"

Respond with ONLY the number (just the number, no text)."""
        
        try:
            text = self._generate_content(prompt)
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                return float(numbers[0])
            return 1.0
        except:
            return 1.0

# Factory function
def create_gemini_processor(food_database: Optional[Dict] = None, model_name: Optional[str] = None) -> GeminiNLPProcessor:
    """Create a Gemini NLP processor
    
    Args:
        food_database: Food database dictionary
        model_name: Model to use (defaults to GEMINI_MODEL env var or 'gemini-2.5-flash')
                   Available models:
                   - Gemini: 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite'
                   - Gemma: 'gemma-3-1b-it', 'gemma-3-4b-it', 'gemma-3-12b-it', 'gemma-3-27b-it'
                   Note: Different models have separate quota limits!
    """
    return GeminiNLPProcessor(food_database, model_name=model_name)

