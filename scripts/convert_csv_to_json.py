#!/usr/bin/env python3
"""
CSV to JSON Food Database Converter
Converts restaurant CSV files to JSON format with hierarchical structure based on Food Type categories.
"""

import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any


def normalize_restaurant_name(filename: str) -> str:
    """Normalize restaurant name from CSV filename to JSON key format"""
    # Remove .csv extension
    name = filename.replace('.csv', '')
    
    # Remove apostrophes
    name = name.replace("'", "").replace("'", "")
    
    # Convert to lowercase
    name = name.lower()
    
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9]+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    return name


def normalize_food_key(food_name: str) -> str:
    """Normalize food name to create clean JSON key"""
    # Remove everything after " - " (portion description)
    if ' - ' in food_name:
        food_name = food_name.split(' - ')[0]
    
    # Remove parenthetical portions like "(95g)", "(3 oz Portion)", etc.
    food_name = re.sub(r'\s*\([^)]*\)\s*', '', food_name)
    
    # Handle quotes like "12"" → 12_inch
    food_name = food_name.replace('"', ' inch')
    food_name = food_name.replace('""', ' inch')
    
    # Replace special characters
    food_name = food_name.replace('&', 'and')
    food_name = food_name.replace('/', '_or_')
    food_name = food_name.replace("'", "")
    
    # Convert to lowercase
    food_name = food_name.lower()
    
    # Replace spaces and special characters with underscores
    food_name = re.sub(r'[^a-z0-9]+', '_', food_name)
    
    # Remove leading/trailing underscores
    food_name = food_name.strip('_')
    
    # Handle empty or very short keys
    if len(food_name) < 2:
        food_name = f"item_{food_name}"
    
    return food_name


def parse_numeric_value(value: str) -> float:
    """Parse numeric value handling special cases"""
    if not value or value.strip() == '':
        return 0.0
    
    value = value.strip()
    
    # Handle "< 1" pattern
    if '<' in value:
        # Extract number if present, otherwise default to 0.5
        numbers = re.findall(r'\d+\.?\d*', value)
        if numbers:
            return float(numbers[0]) / 2  # Half of the threshold
        return 0.5
    
    # Handle ranges (e.g., "1-2" → take midpoint or first value)
    if '-' in value and not value.startswith('-'):
        parts = value.split('-')
        if len(parts) == 2:
            try:
                first = float(parts[0].strip())
                return first  # Use first value
            except:
                pass
    
    # Try to convert to float
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def parse_food_type_for_nesting(food_type: str, restaurant: str) -> List[str]:
    """
    Parse Food Type to determine nesting path
    Returns list of keys representing the path: [category, subcategory, ...]
    """
    if not food_type or food_type.strip() == '':
        return []
    
    food_type = food_type.strip()
    path = []
    
    # Restaurant-specific handling
    restaurant_lower = restaurant.lower()
    
    # Ginger and Soy: All go under "bowl"
    if restaurant_lower == "ginger and soy":
        if food_type in ["Base", "Protein", "Toppings", "Sauce"]:
            return ["bowl", food_type.lower()]
    
    # Il Forno: Premade vs Custom, Pasta vs Pizza
    elif restaurant_lower == "il forno":
        if food_type == "Premade Pasta":
            return ["premade_pastas"]
        elif food_type == "Premade Pizza":
            return ["premade_pizzas"]
        elif food_type.startswith("Pasta - "):
            component = food_type.replace("Pasta - ", "").lower().replace(" ", "_")
            return ["custom_pasta", component]
        elif food_type.startswith("Pizza - "):
            component = food_type.replace("Pizza - ", "").lower().replace(" ", "_")
            return ["custom_pizza", component]
    
    # Sazon: Nested by meal type
    elif restaurant_lower == "sazon":
        if food_type in ["Sauce", "Sides"]:
            return ["extras", food_type.lower()]
        elif food_type.startswith("Quesedilla "):
            component = food_type.replace("Quesedilla ", "").lower().replace(" ", "_")
            return ["quesedilla", component]
        elif food_type.startswith("Taco "):
            component = food_type.replace("Taco ", "").lower().replace(" ", "_")
            return ["taco", component]
        elif food_type.startswith("Bowl "):
            component = food_type.replace("Bowl ", "").lower().replace(" ", "_")
            return ["bowl", component]
        elif food_type.startswith("Burrito "):
            if food_type == "Burrito Portion":
                return ["burrito", "base"]  # Treat as base/protein
            else:
                component = food_type.replace("Burrito ", "").lower().replace(" ", "_")
                return ["burrito", component]
    
    # The Skillet: All top-level
    elif restaurant_lower == "the skillet":
        category = food_type.lower().replace("/", "_").replace(" ", "_")
        return [category]
    
    # The Pitchfork: Quesedilla flat, others top-level
    elif restaurant_lower == "the pitchfork":
        if food_type == "Quesedilla":
            return ["quesedilla"]
        else:
            category = food_type.lower().replace("/", "_").replace(" ", "_")
            return [category]
    
    # Sprout: Bowl nested, others top-level
    elif restaurant_lower == "sprout":
        if food_type.startswith("Bowl "):
            component = food_type.replace("Bowl ", "").lower().replace(" ", "_")
            return ["bowl", component]
        else:
            category = food_type.lower().replace("/", "_").replace(" ", "_")
            return [category]
    
    # Red Mango: Power Bowl nested, others top-level
    elif restaurant_lower == "red mango":
        if food_type.startswith("Power Bowl "):
            component = food_type.replace("Power Bowl ", "").lower().replace(" ", "_")
            return ["power_bowl", component]
        else:
            # Named items or "Base" go as top-level
            category = food_type.lower().replace(" ", "_").replace("&", "and")
            return [category]
    
    # It's Thyme: All top-level
    elif restaurant_lower == "it's thyme":
        category = food_type.lower().replace(" ", "_")
        return [category]
    
    # Default: Use food type as top-level category
    else:
        category = food_type.lower().replace("/", "_").replace(" ", "_")
        return [category] if category else []


def convert_csv_row_to_food_data(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert CSV row to food data dictionary with normalized field names"""
    return {
        'food_name': row.get('Food Name', '').strip(),
        'calories': parse_numeric_value(row.get('Calories', '0')),
        'fat_g': parse_numeric_value(row.get('Fat', '0')),
        'sat_fat_g': parse_numeric_value(row.get('Saturated Fat', '0')),
        'trans_fat_g': parse_numeric_value(row.get('Trans Fat', '0')),
        'chol_mg': parse_numeric_value(row.get('Cholesterol', '0')),
        'sodium_mg': parse_numeric_value(row.get('Sodium', '0')),
        'potassium_mg': parse_numeric_value(row.get('Potassium', '0')),
        'carbs_g': parse_numeric_value(row.get('Carbs', '0')),
        'dietary_fiber_g': parse_numeric_value(row.get('Dietary Fiber', '0')),
        'sugars_g': parse_numeric_value(row.get('Sugars', '0')),
        'protein_g': parse_numeric_value(row.get('Protein', '0'))
    }


def nest_data_at_path(data: Dict, path: List[str], food_key: str, food_data: Dict) -> Dict:
    """Nest food data at the specified path in the dictionary"""
    current = data
    
    # Navigate/create path
    for key in path:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Add food item at final location
    current[food_key] = food_data
    
    return data


def convert_csv_to_json(csv_path: str, output_path: str) -> Dict[str, Any]:
    """Convert a single CSV file to JSON format"""
    restaurant_data = {}
    has_food_type = False
    
    # Use filename as source of truth for restaurant name (preserves "The" prefix)
    filename = Path(csv_path).stem
    restaurant_key = normalize_restaurant_name(filename)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            return restaurant_data
        
        # Check if Food Type column exists
        first_row = rows[0]
        has_food_type = 'Food Type' in first_row
        
        # Get restaurant name from CSV for Food Type parsing (might differ from filename)
        restaurant_name_from_csv = first_row.get('Restaurant', '')
        if not restaurant_name_from_csv:
            restaurant_name_from_csv = filename
        
        restaurant_data[restaurant_key] = {}
        
        # Process each row
        for row in rows:
            food_name = row.get('Food Name', '').strip()
            if not food_name:
                continue
            
            # Convert to food data
            food_data = convert_csv_row_to_food_data(row)
            
            # Get food key
            food_key = normalize_food_key(food_name)
            
            # Handle duplicate food keys (add suffix if needed)
            if has_food_type:
                food_type = row.get('Food Type', '').strip()
                if food_type:
                    path = parse_food_type_for_nesting(food_type, restaurant_name_from_csv)
                    if path:
                        # Nested structure - check for duplicates at path
                        target_dict = restaurant_data[restaurant_key]
                        for key in path:
                            if key not in target_dict:
                                target_dict[key] = {}
                            target_dict = target_dict[key]
                        
                        # Handle duplicate keys at same level
                        original_key = food_key
                        counter = 1
                        while food_key in target_dict:
                            food_key = f"{original_key}_{counter}"
                            counter += 1
                        
                        target_dict[food_key] = food_data
                    else:
                        # Flat structure at restaurant level
                        original_key = food_key
                        counter = 1
                        while food_key in restaurant_data[restaurant_key]:
                            food_key = f"{original_key}_{counter}"
                            counter += 1
                        restaurant_data[restaurant_key][food_key] = food_data
                else:
                    # No food type, use flat structure
                    original_key = food_key
                    counter = 1
                    while food_key in restaurant_data[restaurant_key]:
                        food_key = f"{original_key}_{counter}"
                        counter += 1
                    restaurant_data[restaurant_key][food_key] = food_data
            else:
                # No Food Type column, use flat structure
                original_key = food_key
                counter = 1
                while food_key in restaurant_data[restaurant_key]:
                    food_key = f"{original_key}_{counter}"
                    counter += 1
                restaurant_data[restaurant_key][food_key] = food_data
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(restaurant_data, f, indent=2, ensure_ascii=False)
    
    return restaurant_data


def convert_all_csvs(data_dir: str = 'data', output_dir: str = 'data'):
    """Convert all CSV files in data directory to JSON format"""
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    csv_files = list(data_path.glob('*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {data_dir}")
        return
    
    all_restaurants = {}
    
    for csv_file in sorted(csv_files):
        print(f"Converting {csv_file.name}...")
        
        # Output JSON file (normalized name)
        normalized_name = normalize_restaurant_name(csv_file.name)
        json_filename = normalized_name + '.json'
        json_path = output_path / json_filename
        
        try:
            restaurant_data = convert_csv_to_json(str(csv_file), str(json_path))
            all_restaurants.update(restaurant_data)
            print(f"  ✓ Created {json_filename}")
        except Exception as e:
            print(f"  ✗ Error converting {csv_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Also create a consolidated file with all restaurants
    consolidated_path = output_path / 'all_restaurants.json'
    with open(consolidated_path, 'w', encoding='utf-8') as f:
        json.dump(all_restaurants, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Created consolidated file: all_restaurants.json")
    print(f"✓ Converted {len(csv_files)} CSV files to JSON")


if __name__ == '__main__':
    # Get script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data'
    
    print("Starting CSV to JSON conversion...")
    print(f"Data directory: {data_dir}")
    
    convert_all_csvs(str(data_dir), str(data_dir))
    
    print("\nConversion complete!")
