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
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

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
            model_name: Model to use (defaults to GEMINI_MODEL env var or 'gemma-3-12b-it')
                       Gemini models: 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite'
                       Gemma models: 'gemma-3-1b-it', 'gemma-3-4b-it', 'gemma-3-12b-it', 'gemma-3-27b-it'
                       Note: Different models have separate quota limits!
        """
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemma-3-12b-it')
        
        if NEW_SDK:
            self.client = google_genai.Client(api_key=api_key)
            print(f"Gemini client loaded (new SDK - {self.model_name})")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini model loaded (old SDK - {self.model_name})")
        
        self.last_request_time = 0
        if 'gemma' in self.model_name.lower():
            self.min_request_interval = 2
            print(f"Using Gemma rate limits: 30 req/min, 14.4k req/day")
        else:
            self.min_request_interval = 12
            print(f"Using Gemini rate limits: 5 req/min, 20 req/day (free tier)")
        
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
        
        print("Gemini NLP Processor ready")
    
    def _rate_limit(self):
        """Enforce rate limiting for free tier (5 requests per minute)"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            print(f"Rate limiting: waiting {sleep_time:.1f}s...")
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
        """Load all restaurant food databases from JSON files"""
        from config import Config
        import glob
        
        # Get data directory path - use config path or default to 'data' relative to project root
        if hasattr(Config, 'FOOD_DATABASE_PATH'):
            data_dir = os.path.dirname(Config.FOOD_DATABASE_PATH)
            if not os.path.isabs(data_dir):
                # Relative path, make absolute relative to config.py location
                config_dir = os.path.dirname(os.path.abspath(Config.__file__ if hasattr(Config, '__file__') else __file__))
                data_dir = os.path.join(config_dir, data_dir)
        else:
            # Fallback to 'data' directory relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'data')
        
        # Ensure directory exists
        if not os.path.exists(data_dir):
            print(f"  Data directory not found: {data_dir}")
            return {}
        
        # Load all restaurant JSON files
        restaurant_files = glob.glob(os.path.join(data_dir, '*.json'))
        
        # Filter out non-restaurant files (snacks.json, gym_workouts.json, wu_foods.json, all_restaurants.json)
        exclude_files = {'snacks.json', 'gym_workouts.json', 'wu_foods.json', 'all_restaurants.json'}
        restaurant_files = [f for f in restaurant_files if os.path.basename(f) not in exclude_files]
        
        all_restaurants = {}
        
        for json_file in sorted(restaurant_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    restaurant_data = json.load(f)
                    all_restaurants.update(restaurant_data)
                    restaurant_name = list(restaurant_data.keys())[0] if restaurant_data else 'unknown'
                    # Count total food items recursively
                    def count_items(d):
                        count = 0
                        if isinstance(d, dict):
                            for v in d.values():
                                if isinstance(v, dict):
                                    if 'calories' in v:
                                        count += 1  # Food item
                                    else:
                                        count += count_items(v)  # Category, recurse
                        return count
                    item_count = sum(count_items(v) for v in restaurant_data.values())
                    print(f"  Loaded {restaurant_name} ({item_count} items) from {os.path.basename(json_file)}")
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")
                import traceback
                traceback.print_exc()
        
        if not all_restaurants:
            print("  No restaurant databases found, trying fallback...")
            # Try to load old wu_foods.json as fallback
            try:
                if hasattr(Config, 'FOOD_DATABASE_PATH') and os.path.exists(Config.FOOD_DATABASE_PATH):
                    with open(Config.FOOD_DATABASE_PATH, 'r') as f:
                        fallback_data = json.load(f)
                        print(f"  Loaded fallback from {Config.FOOD_DATABASE_PATH}")
                        return fallback_data
            except FileNotFoundError:
                print("  No food database files found")
                return {}
        
        return all_restaurants
    
    def _load_snacks_database(self):
        """Load snacks database from file"""
        try:
            from config import Config
            with open(Config.SNACKS_DATABASE_PATH, 'r') as f:
                snacks_db = json.load(f)
                print(" Snacks database loaded")
                return snacks_db
        except FileNotFoundError:
            print("  Snacks database not found, skipping")
            return {}
    
    def _get_restaurant_nicknames(self):
        """Map restaurant nicknames to normalized restaurant keys"""
        return {
            'kraft': 'the_devils_krafthouse',
            'krafthouse': 'the_devils_krafthouse',
            'skillet': 'the_skillet',
            'pitch': 'the_pitchfork',
            'pitchfork': 'the_pitchfork',
            'gsoy': 'ginger_and_soy',
            'ginger and soy': 'ginger_and_soy',
            'ginger & soy': 'ginger_and_soy',
            'gothic': 'gothic_grill',
        }
    
    def _get_restaurant_variations(self, restaurant_key):
        """Get all variations (nickname, normalized, with spaces) for a restaurant key"""
        variations = []
        seen = set()
        
        # Helper to add variation if not seen
        def add_variation(var):
            var_lower = var.lower()
            if var_lower not in seen:
                seen.add(var_lower)
                variations.append(var)
        
        # Add normalized key
        add_variation(restaurant_key)
        
        # Add version with spaces
        restaurant_spaces = restaurant_key.replace('_', ' ')
        if restaurant_spaces != restaurant_key:
            add_variation(restaurant_spaces)
        
        # Add nicknames (reverse lookup)
        nicknames_map = self._get_restaurant_nicknames()
        for nickname, normalized in nicknames_map.items():
            if normalized == restaurant_key:
                add_variation(nickname)
                # Also add nickname with space/underscore variations
                if ' ' in nickname:
                    add_variation(nickname.replace(' ', '_'))
                elif '_' in nickname:
                    add_variation(nickname.replace('_', ' '))
        
        return variations
    
    def _flatten_food_database(self, raw_db):
        """Flatten nested food database structure into a flat dict for easier lookup
        
        Handles hierarchical structures like:
        - {"restaurant": {"category": {"food": {...}}}} (nested)
        - {"restaurant": {"food": {...}}} (flat)
        - {"restaurant": {"category": {"subcategory": {"food": {...}}}}} (deeply nested)
        
        Output: Multiple lookup keys prioritizing "restaurant food" order.
        Also includes nickname variations (e.g., "kraft", "gsoy", "skillet", "pitch").
        """
        flattened = {}
        if not raw_db:
            return flattened
        
        def traverse_and_flatten(current_dict, path_prefix=None, restaurant=None):
            """Recursively traverse nested dictionary and flatten"""
            if path_prefix is None:
                path_prefix = []
            
            for key, value in current_dict.items():
                if isinstance(value, dict):
                    # Check if this is a food item (has nutrition data - calories field is definitive)
                    # Food items have 'calories' field, categories don't
                    if 'calories' in value:
                        # This is a food item
                        food_key = key
                        food_data = value.copy()
                        
                        # Add restaurant name to food data
                        if restaurant:
                            food_data['restaurant'] = restaurant
                        
                        # Create various search keys for lookup
                        search_keys = []
                        
                        # 1. Just the food key (e.g., "brown_rice")
                        search_keys.append(food_key)
                        
                        # 2. Food key with spaces (e.g., "brown rice")
                        food_key_spaces = food_key.replace('_', ' ')
                        if food_key_spaces != food_key:
                            search_keys.append(food_key_spaces)
                        
                        # 3. With restaurant prefix (PRIORITY: restaurant comes FIRST in user messages)
                        # e.g., "kraft quesadilla", "gsoy brown rice", "skillet omelette"
                        if restaurant:
                            # Get all restaurant variations (normalized, spaces, nicknames)
                            restaurant_variations = self._get_restaurant_variations(restaurant)
                            
                            for restaurant_var in restaurant_variations:
                                # Priority 1: Restaurant + food (primary search pattern - user says "restaurant food")
                                search_keys.append(f"{restaurant_var} {food_key}")
                                search_keys.append(f"{restaurant_var} {food_key_spaces}")
                                
                                # Priority 2: Food from restaurant (less common but valid pattern)
                                search_keys.append(f"{food_key} from {restaurant_var}")
                                search_keys.append(f"{food_key_spaces} from {restaurant_var}")
                                
                                # With category path: "restaurant category food"
                                if path_prefix:
                                    category_path = ' '.join(path_prefix)
                                    search_keys.append(f"{restaurant_var} {category_path} {food_key}")
                                    search_keys.append(f"{restaurant_var} {category_path} {food_key_spaces}")
                                    
                                    # Also "food from restaurant" with category
                                    search_keys.append(f"{food_key_spaces} from {restaurant_var}")
                                    
                                    # Also without underscores in category path
                                    category_path_spaces = ' '.join([p.replace('_', ' ') for p in path_prefix])
                                    if category_path_spaces != category_path:
                                        search_keys.append(f"{restaurant_var} {category_path_spaces} {food_key}")
                                        search_keys.append(f"{restaurant_var} {category_path_spaces} {food_key_spaces}")
                            
                            # Also add reverse order without "from" (lowest priority - user rarely says "food restaurant")
                            restaurant_spaces = restaurant.replace('_', ' ')
                            search_keys.append(f"{food_key} {restaurant}")
                            search_keys.append(f"{food_key_spaces} {restaurant}")
                            search_keys.append(f"{food_key} {restaurant_spaces}")
                            search_keys.append(f"{food_key_spaces} {restaurant_spaces}")
                        
                        # 4. With category path (without restaurant)
                        if path_prefix:
                            category_path = ' '.join(path_prefix)
                            search_keys.append(f"{category_path} {food_key}")
                            search_keys.append(f"{category_path} {food_key_spaces}")
                        
                        # 5. Just food name variations (remove common prefixes/suffixes for better matching)
                        # e.g., "brown rice" from "brown rice bowl base"
                        if food_key_spaces and len(food_key_spaces) > 5:  # Only for longer names
                            # Extract main food name (remove common suffixes)
                            main_name = food_key_spaces
                            for suffix in [' bowl', ' base', ' portion', ' taco', ' protein', ' toppings', ' sauce']:
                                if main_name.endswith(suffix):
                                    main_name = main_name[:-len(suffix)].strip()
                                    break
                            if main_name != food_key_spaces and len(main_name) > 2:
                                search_keys.append(main_name)
                                if restaurant:
                                    # Add with restaurant variations
                                    restaurant_variations = self._get_restaurant_variations(restaurant)
                                    for restaurant_var in restaurant_variations:
                                        # Restaurant first (most common)
                                        search_keys.append(f"{restaurant_var} {main_name}")
                                        # Food from restaurant (less common)
                                        search_keys.append(f"{main_name} from {restaurant_var}")
                                    # Lower priority reverse order without "from"
                                    restaurant_spaces = restaurant.replace('_', ' ')
                                    search_keys.append(f"{main_name} {restaurant_spaces}")
                        
                        # Add all search keys to flattened dict
                        for search_key in search_keys:
                            search_key_lower = search_key.lower().strip()
                            # Use best match (prefer exact matches, then longer matches)
                            if search_key_lower not in flattened:
                                flattened[search_key_lower] = food_data
                            else:
                                # If key already exists, prefer the one with more context (longer path)
                                existing = flattened[search_key_lower]
                                if len(search_key_lower) > len(str(existing.get('food_name', ''))):
                                    flattened[search_key_lower] = food_data
                        
                        # Handle common misspellings/variations
                        if 'quesadilla' in food_key or 'quesedilla' in food_key:
                            for spelling in ['quesadilla', 'quesedilla']:
                                # Replace with each spelling variation
                                for search_key in search_keys:
                                    variant_key = search_key.replace('quesadilla', spelling).replace('quesedilla', spelling).lower()
                                    if variant_key not in flattened:
                                        flattened[variant_key] = food_data
                    else:
                        # This is a category/subcategory, continue traversing
                        new_path = path_prefix + [key]
                        traverse_and_flatten(value, new_path, restaurant)
                else:
                    # Leaf value that's not a dict - shouldn't happen in food database
                    pass
        
        # Process each restaurant
        for restaurant, restaurant_data in raw_db.items():
            if isinstance(restaurant_data, dict):
                traverse_and_flatten(restaurant_data, [], restaurant)
        
        return flattened
    
    def _load_gym_database(self):
        """Load gym workout database from file"""
        try:
            from config import Config
            with open(Config.GYM_DATABASE_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("  Gym workout database not found, using empty DB")
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
- sleep_logging: User is logging sleep (e.g., "slept at 1:30", "up at 8", "slept 1:30-8", "went to bed at 11", "woke up at 7")
- reminder_set: User wants to set a reminder (if message contains a time/date like "at 5pm", "tomorrow", "in 1 hour", etc., classify as reminder_set even if it also sounds like a todo)
- todo_add: User wants to add a todo item (only if there's NO specific time/date mentioned)
- assignment_add: User is adding a school assignment (e.g., "CS101 homework 3 due Friday", "Math assignment due tomorrow", "History essay due March 20", mentions class name/number and due date)
- water_goal_set: User wants to set a custom water goal for a specific day (e.g., "my water goal for tomorrow is 5L", "set water goal to 3L today")
- stats_query: User is asking about their stats/totals (e.g., "how much have I eaten", "how much water have I drank", "what's my total for today", "show me my stats", "how much did I sleep last night")
- fact_storage: User is storing a fact/information (e.g., "WiFi password is duke-guest-2025", "locker code 4312", "parking spot B17", "dentist is Dr. Patel")
- fact_query: User is asking for stored information (e.g., "what's the WiFi password", "where did I park", "what's my locker code", "who is my dentist")
- task_complete: User is marking a task/reminder as complete (e.g., "called mom", "did groceries", "finished homework", "done with that", "completed the task")
- vague_completion: User is indicating completion but message is vague/ambiguous (e.g., "just finished", "done", "finished", "all done", "complete" without specific details)
- what_should_i_do: User is asking what they should do now (e.g., "what should I do now", "what's next", "what do I do", "suggest something", "I'm bored, what should I do?")
- food_suggestion: User is asking for food suggestions (e.g., "what should I eat", "something high in protein", "high protein and low calories", "suggest food")
- undo_edit: User wants to undo or edit a previous action (e.g., "undo last", "delete last food", "edit last water", "remove last reminder", "undo that")
- confirmation: User is confirming or denying something (e.g., "yes", "yep", "correct", "no", "nope", "that's right")
- unknown: Doesn't match any category

IMPORTANT: 
- If a message mentions a class name/number AND a due date, classify as "assignment_add" (e.g., "CS101 homework due Friday")
- If a message has BOTH a task/todo AND a time/date (e.g., "I need to call mama at 5pm tomorrow"), classify it as "reminder_set" because reminders are more specific than todos.

Message: "{message}"

Respond with ONLY the intent name, nothing else."""
        
        try:
            intent = self._generate_content(prompt).lower()
            
            # Validate intent
            valid_intents = ['water_logging', 'food_logging', 'gym_workout', 'sleep_logging', 'reminder_set', 'todo_add', 'assignment_add', 'water_goal_set', 'stats_query', 'fact_storage', 'fact_query', 'task_complete', 'vague_completion', 'what_should_i_do', 'food_suggestion', 'undo_edit', 'confirmation', 'unknown']
            if intent in valid_intents:
                return intent
            else:
                # Try to extract intent from response
                for valid_intent in valid_intents:
                    if valid_intent in intent:
                        return valid_intent
                return 'unknown'
        except Exception as e:
            print(f" Error classifying intent: {e}")
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
            print(f" Error extracting entities: {e}")
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
            print(f" Error parsing water amount: {e}")
            return None
    
    def parse_food(self, message: str) -> Optional[Dict]:
        """Parse food information from message, extracting macros if provided"""
        # Get nickname mapping for the prompt
        nicknames_map = self._get_restaurant_nicknames()
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
   - "kraft" = "the_devils_krafthouse" (also "krafthouse")
   - "skillet" = "the_skillet"
   - "pitch" or "pitchfork" = "the_pitchfork"
   - "gsoy" = "ginger_and_soy"
   - "gothic" = "gothic_grill"
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

EXAMPLES:
- "just ate a kraft quesedilla" → {{"food_name": "quesedilla", "portion_multiplier": 1.0, "restaurant": "kraft"}}
- "just ate half of an ice cream sundae from gothic" → {{"food_name": "ice cream sundae", "portion_multiplier": 0.5, "restaurant": "gothic"}}
- "gsoy brown rice bowl" → {{"food_name": "brown rice bowl", "portion_multiplier": 1.0, "restaurant": "gsoy"}}
- "double skillet omelette" → {{"food_name": "omelette", "portion_multiplier": 2.0, "restaurant": "skillet"}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self._generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                food_data = json.loads(json_match.group())
                
                # Look up in food database (now flattened)
                food_name = food_data.get('food_name', '').lower().strip()
                restaurant = food_data.get('restaurant', '').lower().strip()
                
                # Build search terms prioritizing "restaurant food" order (user always says restaurant first)
                search_terms = []
                
                # Normalize restaurant name (handle nicknames)
                if restaurant:
                    # Check if it's a nickname and get the normalized name
                    nicknames_map = self._get_restaurant_nicknames()
                    normalized_restaurant = nicknames_map.get(restaurant, restaurant)
                    if normalized_restaurant != restaurant:
                        restaurant = normalized_restaurant
                    
                    # Get all restaurant variations (normalized, spaces, nickname)
                    restaurant_variations = self._get_restaurant_variations(restaurant)
                    
                    # Get food name variations
                    food_name_spaces = food_name.replace('_', ' ')
                    
                    # Priority 1: "restaurant food" (exact match with restaurant first - most common)
                    for restaurant_var in restaurant_variations:
                        search_terms.append(f"{restaurant_var} {food_name}")
                        if food_name_spaces != food_name:
                            search_terms.append(f"{restaurant_var} {food_name_spaces}")
                    
                    # Priority 2: "food from restaurant" (less common but valid pattern)
                    for restaurant_var in restaurant_variations:
                        search_terms.append(f"{food_name} from {restaurant_var}")
                        if food_name_spaces != food_name:
                            search_terms.append(f"{food_name_spaces} from {restaurant_var}")
                    
                    # Priority 3: Just food name (lower priority - no restaurant context)
                    search_terms.append(food_name)
                    if food_name_spaces != food_name:
                        search_terms.append(food_name_spaces)
                    
                    # Priority 4: "food restaurant" (lowest priority - reverse order without "from")
                    for restaurant_var in restaurant_variations:
                        search_terms.append(f"{food_name} {restaurant_var}")
                        if food_name_spaces != food_name:
                            search_terms.append(f"{food_name_spaces} {restaurant_var}")
                else:
                    # No restaurant specified - just search food name
                    search_terms = [food_name]
                    food_name_spaces = food_name.replace('_', ' ')
                    if food_name_spaces != food_name:
                        search_terms.append(food_name_spaces)
                
                # Look for best match with priority scoring
                best_match = None
                best_score = 0
                
                # Get restaurant variations for matching
                restaurant_variations_for_matching = []
                if restaurant:
                    restaurant_variations_for_matching = self._get_restaurant_variations(restaurant)
                    # Also add original restaurant name
                    restaurant_variations_for_matching.append(restaurant)
                    # Add lowercase versions
                    restaurant_variations_for_matching.extend([r.lower() for r in restaurant_variations_for_matching])
                
                for key, value in self.food_db.items():
                    key_lower = key.lower().strip()
                    
                    # STRICT: If restaurant is specified, ONLY consider matches that include the restaurant
                    if restaurant and restaurant_variations_for_matching:
                        # Check if ANY restaurant variation appears in the key
                        restaurant_in_key = any(rest_var.lower() in key_lower for rest_var in restaurant_variations_for_matching)
                        if not restaurant_in_key:
                            # Skip this match entirely - restaurant doesn't match
                            continue
                    
                    # Check each search term and score based on priority and match quality
                    for i, term in enumerate(search_terms):
                        term_lower = term.lower().strip()
                        
                        # Calculate match score
                        score = 0
                        match_type = None
                        
                        # Exact match gets highest score
                        if term_lower == key_lower:
                            score = 200 - (i * 2)  # Earlier search terms (restaurant-first) get higher scores
                            match_type = 'exact'
                        # Check if search term starts with restaurant (restaurant-first pattern)
                        elif restaurant and term_lower.startswith(restaurant.lower()) and term_lower in key_lower:
                            score = 150 - (i * 2)  # Restaurant-first matches get high priority
                            match_type = 'restaurant_first'
                        # Check if restaurant is in the key (any position) - already verified above
                        elif restaurant and restaurant.lower() in key_lower and term_lower in key_lower:
                            score = 100 - (i * 1)
                            match_type = 'restaurant_anywhere'
                        # Partial match (search term contains key or vice versa)
                        # Only allow if restaurant matches (already checked above)
                        elif term_lower in key_lower:
                            score = 50 - (i * 0.5)
                            match_type = 'contains'
                        elif key_lower in term_lower:
                            score = 40 - (i * 0.5)
                            match_type = 'key_contains'
                        
                        # Bonus: Exact match on food name part (even without restaurant)
                        if food_name and food_name in key_lower:
                            score += 10
                        
                        if score > best_score:
                            best_score = score
                            best_match = (key, value)
                
                # Get portion multiplier with fallback
                portion_multiplier = food_data.get('portion_multiplier')
                if portion_multiplier is None:
                    # Fallback: try to parse from message if Gemini didn't extract it
                    try:
                        portion_multiplier = self.parse_portion_multiplier(message)
                    except:
                        portion_multiplier = 1.0
                else:
                    try:
                        portion_multiplier = float(portion_multiplier)
                    except (ValueError, TypeError):
                        # Invalid value, try fallback parser
                        try:
                            portion_multiplier = self.parse_portion_multiplier(message)
                        except:
                            portion_multiplier = 1.0
                
                # Ensure portion_multiplier is valid (between 0 and 10)
                if portion_multiplier is None or portion_multiplier < 0:
                    portion_multiplier = 1.0
                elif portion_multiplier > 10:
                    portion_multiplier = 10.0  # Cap at 10x for safety
                
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
                    # Extract food name - use food_name from value if available, otherwise use key
                    if 'food_name' in value:
                        food_name = value['food_name']
                    else:
                        food_name = key.replace('_', ' ')
                        # Remove restaurant prefix if it exists
                        matched_restaurant = value.get('restaurant', '')
                        if matched_restaurant:
                            restaurant_lower = matched_restaurant.lower().replace('_', ' ')
                            food_name_lower = food_name.lower()
                            if food_name_lower.startswith(restaurant_lower + ' '):
                                food_name = food_name[len(restaurant_lower) + 1:]
                            elif food_name_lower.endswith(' ' + restaurant_lower):
                                food_name = food_name[:-len(restaurant_lower) - 1]
                    
                    matched_restaurant = value.get('restaurant', '')
                    
                    # Convert database fields (protein_g, carbs_g, fat_g) to expected format (protein, carbs, fat)
                    # Handle both old format (protein, carbs, fat) and new format (protein_g, carbs_g, fat_g)
                    db_calories = value.get('calories', 0)
                    db_protein = value.get('protein_g', value.get('protein', 0))
                    db_carbs = value.get('carbs_g', value.get('carbs', 0))
                    db_fat = value.get('fat_g', value.get('fat', 0))
                    db_fiber = value.get('dietary_fiber_g', value.get('fiber', 0))
                    
                    # Use provided macros if available, otherwise use database values
                    if has_provided_macros:
                        food_data_dict = {
                            'calories': calories if calories is not None else db_calories,
                            'protein': protein_g if protein_g is not None else db_protein,
                            'carbs': carbs_g if carbs_g is not None else db_carbs,
                            'fat': fat_g if fat_g is not None else db_fat,
                            'fiber': dietary_fiber_g if dietary_fiber_g is not None else db_fiber
                        }
                    else:
                        # Convert to expected format (protein, carbs, fat instead of protein_g, carbs_g, fat_g)
                        food_data_dict = {
                            'calories': db_calories,
                            'protein': db_protein,
                            'carbs': db_carbs,
                            'fat': db_fat,
                            'fiber': db_fiber
                        }
                    
                    return {
                        'food_name': food_name,
                        'food_data': food_data_dict,
                        'portion_multiplier': portion_multiplier,
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
                        'portion_multiplier': portion_multiplier,
                        'restaurant': food_data.get('restaurant')
                    }
                
                # If not found and no macros provided, return basic structure (will log as unknown)
                return {
                    'food_name': food_data.get('food_name', ''),
                    'food_data': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0},
                    'portion_multiplier': portion_multiplier,
                    'restaurant': food_data.get('restaurant')
                }
            return None
        except Exception as e:
            print(f" Error parsing food: {e}")
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
                        
                        # Normalize sets format - convert old format to new format if needed
                        if 'sets' in exercise and isinstance(exercise['sets'], int):
                            # Old format: sets is a number, weight/reps are single values
                            sets_count = exercise['sets']
                            weight = exercise.get('weight')
                            reps = exercise.get('reps')
                            exercise['sets'] = [
                                {'weight': weight, 'reps': reps, 'set_number': i+1}
                                for i in range(sets_count)
                            ]
                        elif 'sets' not in exercise or not exercise.get('sets'):
                            # No sets specified, create one from weight/reps if available
                            weight = exercise.get('weight')
                            reps = exercise.get('reps')
                            if weight or reps:
                                exercise['sets'] = [{'weight': weight, 'reps': reps, 'set_number': 1}]
                
                workout['date'] = datetime.now().isoformat()
                workout['message'] = message
                return workout
            return None
        except Exception as e:
            print(f" Error parsing gym workout: {e}")
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
            print(f" Error parsing reminder: {e}")
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

Examples:
- "CS101 homework 3 due Friday" -> {{"class_name": "CS101", "assignment_name": "homework 3", "due_date": "..."}}
- "Math assignment due tomorrow" -> {{"class_name": "Math", "assignment_name": "assignment", "due_date": "..."}}
- "History 201 essay due March 20" -> {{"class_name": "History 201", "assignment_name": "essay", "due_date": "..."}}

Message: "{message}"

Current date/time: {datetime.now().isoformat()}

Respond with ONLY valid JSON, no other text."""
        
        try:
            text = self._generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                assignment = json.loads(json_match.group())
                
                # Parse due_date if it's a string
                if assignment.get('due_date') and isinstance(assignment['due_date'], str):
                    try:
                        due_date = datetime.fromisoformat(assignment['due_date'].replace('Z', '+00:00'))
                        # If no time specified, default to end of day (11:59 PM)
                        if due_date.hour == 0 and due_date.minute == 0 and due_date.second == 0:
                            due_date = due_date.replace(hour=23, minute=59, second=59)
                        assignment['due_date'] = due_date
                    except:
                        # If parsing fails, default to tomorrow end of day
                        assignment['due_date'] = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
                else:
                    # Default to tomorrow end of day if no date provided
                    assignment['due_date'] = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
                
                assignment['created_at'] = datetime.now().isoformat()
                return assignment
            return None
        except Exception as e:
            print(f" Error parsing assignment: {e}")
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
            print(f" Error parsing water goal: {e}")
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

Examples:
- "how much have I eaten" -> {{"food": true, "water": false, "gym": false, "sleep": false, "todos": false, "reminders": false, "all": false}}
- "how much water have I drank" -> {{"food": false, "water": true, "gym": false, "sleep": false, "todos": false, "reminders": false, "all": false}}
- "how much did I sleep last night" -> {{"food": false, "water": false, "gym": false, "sleep": true, "todos": false, "reminders": false, "all": false}}
- "what's on my to do list" -> {{"food": false, "water": false, "gym": false, "sleep": false, "todos": true, "reminders": false, "all": false}}
- "do I have any reminders" -> {{"food": false, "water": false, "gym": false, "sleep": false, "todos": false, "reminders": true, "all": false}}
- "what's my total for today" -> {{"food": true, "water": true, "gym": false, "sleep": false, "todos": false, "reminders": false, "all": true}}
- "show me my stats" -> {{"food": true, "water": true, "gym": true, "sleep": true, "todos": false, "reminders": false, "all": true}}

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
                    'sleep': query_data.get('sleep', False),
                    'todos': query_data.get('todos', False),
                    'reminders': query_data.get('reminders', False),
                    'all': query_data.get('all', False)
                }
            # Default: if unclear, show all
            return {'food': True, 'water': True, 'gym': False, 'sleep': False, 'todos': False, 'reminders': False, 'all': True}
        except Exception as e:
            print(f" Error parsing stats query: {e}")
            # Default: if error, show all
            return {'food': True, 'water': True, 'gym': False, 'todos': False, 'reminders': False, 'all': True}
    
    def parse_date_query(self, message: str) -> Dict[str, Any]:
        """Parse date/timeframe query from message
        
        Returns:
            {
                'type': 'specific_date' or 'timeframe' or None,
                'date': 'YYYY-MM-DD' (if specific_date),
                'timeframe': 'week' or 'month' (if timeframe),
                'count': 1, 2, etc. (number of weeks/months),
                'direction': 'past' or 'future' (defaults to 'past')
            }
        """
        current_date = datetime.now().date()
        message_lower = message.lower()
        
        # Try to extract date/timeframe using Gemini
        prompt = f"""Extract date or timeframe information from this message. Return JSON with:
{{
  "query_type": "specific_date" or "timeframe" or "none",
  "date_str": "YYYY-MM-DD format date if specific_date (e.g., '2024-01-15'), null otherwise",
  "timeframe_type": "week" or "month" or "day" or null (only if query_type is 'timeframe'),
  "timeframe_count": number like 1, 2, 3 (only if query_type is 'timeframe'),
  "timeframe_direction": "past" or "future" (default: "past")
}}

Current date: {current_date.isoformat()}

Handle these patterns:
- "yesterday" -> {{"query_type": "specific_date", "date_str": "{((current_date - timedelta(days=1)).isoformat())}", ...}}
- "today" -> {{"query_type": "specific_date", "date_str": "{current_date.isoformat()}", ...}}
- "last week" -> {{"query_type": "timeframe", "timeframe_type": "week", "timeframe_count": 1, "timeframe_direction": "past", ...}}
- "two weeks ago" -> {{"query_type": "timeframe", "timeframe_type": "week", "timeframe_count": 2, "timeframe_direction": "past", ...}}
- "last month" -> {{"query_type": "timeframe", "timeframe_type": "month", "timeframe_count": 1, "timeframe_direction": "past", ...}}
- "January 15th" or "Jan 15" -> {{"query_type": "specific_date", "date_str": "2024-01-15" (assume current year if year not specified), ...}}
- "January 15, 2024" -> {{"query_type": "specific_date", "date_str": "2024-01-15", ...}}

If no date/timeframe is mentioned, return {{"query_type": "none", ...}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self._generate_content(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                query_type = parsed.get('query_type', 'none')
                
                if query_type == 'specific_date':
                    date_str = parsed.get('date_str')
                    if date_str:
                        try:
                            # Parse and validate date
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
                
                # Fallback: try simple patterns
                if 'yesterday' in message_lower:
                    yesterday = (current_date - timedelta(days=1)).isoformat()
                    return {'type': 'specific_date', 'date': yesterday}
                elif 'today' in message_lower:
                    return {'type': 'specific_date', 'date': current_date.isoformat()}
                elif 'last week' in message_lower or 'past week' in message_lower:
                    return {'type': 'timeframe', 'timeframe': 'week', 'count': 1, 'direction': 'past'}
                elif 'last month' in message_lower or 'past month' in message_lower:
                    return {'type': 'timeframe', 'timeframe': 'month', 'count': 1, 'direction': 'past'}
                elif re.search(r'\d+\s*weeks?\s+ago', message_lower):
                    match = re.search(r'(\d+)\s*weeks?\s+ago', message_lower)
                    if match:
                        count = int(match.group(1))
                        return {'type': 'timeframe', 'timeframe': 'week', 'count': count, 'direction': 'past'}
                
            # No date/timeframe found
            return {'type': None}
        except Exception as e:
            print(f" Error parsing date query: {e}")
            # Fallback to simple patterns
            message_lower = message.lower()
            current_date = datetime.now().date()
            
            if 'yesterday' in message_lower:
                yesterday = (current_date - timedelta(days=1)).isoformat()
                return {'type': 'specific_date', 'date': yesterday}
            elif 'today' in message_lower:
                return {'type': 'specific_date', 'date': current_date.isoformat()}
            elif 'last week' in message_lower:
                return {'type': 'timeframe', 'timeframe': 'week', 'count': 1, 'direction': 'past'}
            elif 'last month' in message_lower:
                return {'type': 'timeframe', 'timeframe': 'month', 'count': 1, 'direction': 'past'}
            
            return {'type': None}
    
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
            print(f" Error guessing intent: {e}")
            return None
    
    def parse_portion_multiplier(self, message: str) -> float:
        """Parse portion multiplier from message"""
        prompt = f"""Extract portion multiplier from this message:
- "half" or "half of" = 0.5
- "quarter" or "quarter of" = 0.25
- "double" = 2.0
- "2x" or "2 x" = 2.0
- "1.5" or "one and a half" = 1.5
- Numbers like "2 quesadillas" or "3 slices" = use the number (2.0, 3.0, etc.)
- default = 1.0

Examples:
- "half of an ice cream" → 0.5
- "just ate half" → 0.5
- "double portion" → 2.0
- "2 quesadillas" → 2.0
- "one and a half servings" → 1.5

Message: "{message}"

Respond with ONLY the number (0.5, 1.0, 2.0, etc.), nothing else."""
        
        try:
            text = self._generate_content(prompt).lower().strip()
            
            # First try to extract number directly
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                value = float(numbers[0])
                # If we found a number, check if it's part of "half" (0.5) or already a valid multiplier
                if 'half' in text or '0.5' in text or '.5' in text:
                    return 0.5
                elif value >= 0.1 and value <= 10:
                    return value
            
            # Check for word-based multipliers
            if 'half' in text:
                return 0.5
            elif 'quarter' in text:
                return 0.25
            elif 'double' in text:
                return 2.0
            elif 'triple' in text:
                return 3.0
            
            return 1.0
        except Exception as e:
            print(f" Error parsing portion multiplier: {e}")
            return 1.0
    
    def parse_food_suggestion(self, message: str) -> Dict:
        """Parse food suggestion query to extract constraints"""
        prompt = f"""Extract food constraints from this message. Return JSON with:
{{
  "high_protein": true/false (user wants high protein),
  "low_protein": true/false (user wants low protein),
  "high_calories": true/false (user wants high calories),
  "low_calories": true/false (user wants low calories),
  "high_carbs": true/false (user wants high carbs),
  "low_carbs": true/false (user wants low carbs),
  "high_fat": true/false (user wants high fat),
  "low_fat": true/false (user wants low fat),
  "restaurant": "restaurant_name" or null (specific restaurant if mentioned),
  "location": "location_name" or null (e.g., "dining hall", "home", "campus")
}}

Examples:
- "what should I eat" -> {{"high_protein": false, "low_protein": false, "high_calories": false, "low_calories": false, "high_carbs": false, "low_carbs": false, "high_fat": false, "low_fat": false, "restaurant": null, "location": null}}
- "something high in protein" -> {{"high_protein": true, "low_protein": false, "high_calories": false, "low_calories": false, "high_carbs": false, "low_carbs": false, "high_fat": false, "low_fat": false, "restaurant": null, "location": null}}
- "high protein and low calories" -> {{"high_protein": true, "low_protein": false, "high_calories": false, "low_calories": true, "high_carbs": false, "low_carbs": false, "high_fat": false, "low_fat": false, "restaurant": null, "location": null}}
- "something from sazon" -> {{"high_protein": false, "low_protein": false, "high_calories": false, "low_calories": false, "high_carbs": false, "low_carbs": false, "high_fat": false, "low_fat": false, "restaurant": "sazon", "location": null}}

Message: "{message}"

Respond with ONLY valid JSON, no other text."""
        
        try:
            response_text = self._generate_content(prompt)
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
            print(f" Error parsing food suggestion: {e}")
            return {}

# Factory function
def create_gemini_processor(food_database: Optional[Dict] = None, model_name: Optional[str] = None) -> GeminiNLPProcessor:
    """Create a Gemini NLP processor
    
    Args:
        food_database: Food database dictionary
        model_name: Model to use (defaults to GEMINI_MODEL env var or 'gemma-3-12b-it')
                   Available models:
                   - Gemini: 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite'
                   - Gemma: 'gemma-3-1b-it', 'gemma-3-4b-it', 'gemma-3-12b-it', 'gemma-3-27b-it'
                   Note: Different models have separate quota limits!
    """
    return GeminiNLPProcessor(food_database, model_name=model_name)

