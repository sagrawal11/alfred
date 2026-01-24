"""
Database Loader
Loads and processes food and gym databases
"""

import os
import json
import glob
from typing import Dict, Optional
from config import Config


class DatabaseLoader:
    """Loads and processes food and gym databases"""
    
    def __init__(self):
        """Initialize database loader"""
        self.food_db = None
        self.gym_db = None
        self.water_bottle_size_ml = Config.WATER_BOTTLE_SIZE_ML
    
    def load_food_database(self) -> Dict:
        """Load all restaurant food databases from JSON files"""
        # Get data directory path
        if hasattr(Config, 'FOOD_DATABASE_PATH'):
            data_dir = os.path.dirname(Config.FOOD_DATABASE_PATH)
            if not os.path.isabs(data_dir):
                config_dir = os.path.dirname(os.path.abspath(Config.__file__ if hasattr(Config, '__file__') else __file__))
                data_dir = os.path.join(config_dir, data_dir)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'data')
        
        if not os.path.exists(data_dir):
            print(f"  Data directory not found: {data_dir}")
            return {}
        
        # Load all restaurant JSON files
        restaurant_files = glob.glob(os.path.join(data_dir, '*.json'))
        exclude_files = {'snacks.json', 'gym_workouts.json', 'wu_foods.json', 'all_restaurants.json'}
        restaurant_files = [f for f in restaurant_files if os.path.basename(f) not in exclude_files]
        
        all_restaurants = {}
        
        for json_file in sorted(restaurant_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    restaurant_data = json.load(f)
                    all_restaurants.update(restaurant_data)
                    restaurant_name = list(restaurant_data.keys())[0] if restaurant_data else 'unknown'
                    item_count = self._count_food_items(restaurant_data)
                    print(f"  Loaded {restaurant_name} ({item_count} items) from {os.path.basename(json_file)}")
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")
        
        if not all_restaurants:
            # Try fallback
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
    
    def _count_food_items(self, d: Dict) -> int:
        """Count food items recursively"""
        count = 0
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, dict):
                    if 'calories' in v:
                        count += 1
                    else:
                        count += self._count_food_items(v)
        return count
    
    def load_snacks_database(self) -> Dict:
        """Load snacks database from file"""
        try:
            with open(Config.SNACKS_DATABASE_PATH, 'r') as f:
                snacks_db = json.load(f)
                print("  Snacks database loaded")
                return snacks_db
        except FileNotFoundError:
            print("  Snacks database not found, skipping")
            return {}
    
    def load_gym_database(self) -> Dict:
        """Load gym workout database from file"""
        try:
            with open(Config.GYM_DATABASE_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("  Gym workout database not found, using empty DB")
            return {}
    
    def get_restaurant_nicknames(self) -> Dict[str, str]:
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
    
    def get_restaurant_variations(self, restaurant_key: str) -> list:
        """Get all variations (nickname, normalized, with spaces) for a restaurant key"""
        variations = []
        seen = set()
        
        def add_variation(var):
            var_lower = var.lower()
            if var_lower not in seen:
                seen.add(var_lower)
                variations.append(var)
        
        add_variation(restaurant_key)
        
        restaurant_spaces = restaurant_key.replace('_', ' ')
        if restaurant_spaces != restaurant_key:
            add_variation(restaurant_spaces)
        
        nicknames_map = self.get_restaurant_nicknames()
        for nickname, normalized in nicknames_map.items():
            if normalized == restaurant_key:
                add_variation(nickname)
                if ' ' in nickname:
                    add_variation(nickname.replace(' ', '_'))
                elif '_' in nickname:
                    add_variation(nickname.replace('_', ' '))
        
        return variations
    
    def flatten_food_database(self, raw_db: Dict) -> Dict:
        """Flatten nested food database structure into a flat dict for easier lookup"""
        flattened = {}
        if not raw_db:
            return flattened
        
        def traverse_and_flatten(current_dict, path_prefix=None, restaurant=None):
            if path_prefix is None:
                path_prefix = []
            
            for key, value in current_dict.items():
                if isinstance(value, dict):
                    if 'calories' in value:
                        # This is a food item
                        food_key = key
                        food_data = value.copy()
                        
                        if restaurant:
                            food_data['restaurant'] = restaurant
                        
                        search_keys = []
                        search_keys.append(food_key)
                        
                        food_key_spaces = food_key.replace('_', ' ')
                        if food_key_spaces != food_key:
                            search_keys.append(food_key_spaces)
                        
                        if restaurant:
                            restaurant_variations = self.get_restaurant_variations(restaurant)
                            for restaurant_var in restaurant_variations:
                                search_keys.append(f"{restaurant_var} {food_key}")
                                search_keys.append(f"{restaurant_var} {food_key_spaces}")
                                search_keys.append(f"{food_key} from {restaurant_var}")
                                search_keys.append(f"{food_key_spaces} from {restaurant_var}")
                                
                                if path_prefix:
                                    category_path = ' '.join(path_prefix)
                                    search_keys.append(f"{restaurant_var} {category_path} {food_key}")
                                    search_keys.append(f"{restaurant_var} {category_path} {food_key_spaces}")
                        
                        if path_prefix:
                            category_path = ' '.join(path_prefix)
                            search_keys.append(f"{category_path} {food_key}")
                            search_keys.append(f"{category_path} {food_key_spaces}")
                        
                        for search_key in search_keys:
                            search_key_lower = search_key.lower().strip()
                            if search_key_lower not in flattened:
                                flattened[search_key_lower] = food_data
                    else:
                        # Category, continue traversing
                        new_path = path_prefix + [key]
                        traverse_and_flatten(value, new_path, restaurant)
        
        for restaurant, restaurant_data in raw_db.items():
            if isinstance(restaurant_data, dict):
                traverse_and_flatten(restaurant_data, [], restaurant)
        
        return flattened
    
    def flatten_gym_database(self, raw_db: Dict) -> Dict:
        """Flatten nested gym database structure"""
        flattened = {}
        if not raw_db:
            return flattened
        
        for muscle_group, exercises in raw_db.items():
            if isinstance(exercises, dict):
                for exercise_key, exercise_data in exercises.items():
                    exercise_data_with_muscle = {**exercise_data, 'muscle_group': muscle_group}
                    
                    flattened[exercise_key] = exercise_data_with_muscle
                    
                    exercise_name = exercise_key.replace('_', ' ')
                    flattened[exercise_name] = exercise_data_with_muscle
                    
                    if 'common_variations' in exercise_data:
                        for variation in exercise_data['common_variations']:
                            flattened[variation.lower()] = exercise_data_with_muscle
                    
                    flattened[f"{muscle_group} {exercise_name}"] = exercise_data_with_muscle
                    flattened[f"{muscle_group} {exercise_key}"] = exercise_data_with_muscle
        
        return flattened
    
    def get_food_database(self) -> Dict:
        """Get flattened food database (loads if not already loaded)"""
        if self.food_db is None:
            raw_food_db = self.load_food_database()
            raw_snacks_db = self.load_snacks_database()
            if raw_snacks_db:
                raw_food_db = {**raw_food_db, **raw_snacks_db}
            self.food_db = self.flatten_food_database(raw_food_db)
        return self.food_db
    
    def get_gym_database(self) -> Dict:
        """Get flattened gym database (loads if not already loaded)"""
        if self.gym_db is None:
            raw_gym_db = self.load_gym_database()
            self.gym_db = self.flatten_gym_database(raw_gym_db)
        return self.gym_db
