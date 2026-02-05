"""
Database Loader
Loads and processes gym database; provides water bottle size for parsing.
Food data is now resolved via USDA/Supabase and other nutrition providers.
Gym data: prefers data/exercises.csv if present, else data/gym_workouts.json.
"""

import csv
import json
import os
from typing import Any, Dict, List

from config import Config


class DatabaseLoader:
    """Loads gym workout database; provides water_bottle_size_ml for water parsing."""

    def __init__(self):
        self.gym_db = None
        self.water_bottle_size_ml = Config.WATER_BOTTLE_SIZE_ML

    def _load_and_flatten_csv(self) -> Dict[str, Dict[str, Any]]:
        """Load exercises.csv and build flattened gym_db (parser-compatible shape)."""
        flattened: Dict[str, Dict[str, Any]] = {}
        path = getattr(Config, "EXERCISES_CSV_PATH", None) or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "exercises.csv"
        )
        if not os.path.isfile(path):
            return flattened
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        continue
                    target_muscles = _parse_json_list(row.get("targetMuscles"))
                    body_parts = _parse_json_list(row.get("bodyParts"))
                    secondary_muscles = _parse_json_list(row.get("secondaryMuscles"))
                    exercise_type = (row.get("exerciseType") or "weight_reps").strip()
                    primary_muscle = (target_muscles[0] if target_muscles else body_parts[0] if body_parts else "") or ""
                    muscle_group = (body_parts[0] if body_parts else target_muscles[0] if target_muscles else "") or primary_muscle
                    entry = {
                        "primary_muscle": primary_muscle,
                        "secondary_muscles": secondary_muscles,
                        "exercise_type": exercise_type,
                        "muscle_group": muscle_group,
                    }
                    key_lower = name.lower().strip()
                    flattened[key_lower] = entry
                    flattened[" ".join(key_lower.split())] = entry
                    if muscle_group:
                        flattened[f"{muscle_group.lower()} {key_lower}".strip()] = entry
                    variations = _parse_json_list(row.get("variations"))
                    for v in variations:
                        if isinstance(v, str) and v.strip():
                            flattened[v.lower().strip()] = entry
        except Exception as e:
            print(f"  Error loading exercises CSV: {e}")
            return {}
        return flattened

    def load_gym_database(self) -> Dict:
        """Load gym workout database from file (JSON; used when CSV not present)."""
        try:
            with open(Config.GYM_DATABASE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def flatten_gym_database(self, raw_db: Dict) -> Dict:
        """Flatten nested gym database structure (for gym_workouts.json)."""
        flattened = {}
        if not raw_db:
            return flattened
        for muscle_group, exercises in raw_db.items():
            if isinstance(exercises, dict):
                for exercise_key, exercise_data in exercises.items():
                    exercise_data_with_muscle = {**exercise_data, "muscle_group": muscle_group}
                    flattened[exercise_key] = exercise_data_with_muscle
                    exercise_name = exercise_key.replace("_", " ")
                    flattened[exercise_name] = exercise_data_with_muscle
                    if "common_variations" in exercise_data:
                        for variation in exercise_data["common_variations"]:
                            flattened[variation.lower()] = exercise_data_with_muscle
                    flattened[f"{muscle_group} {exercise_name}"] = exercise_data_with_muscle
                    flattened[f"{muscle_group} {exercise_key}"] = exercise_data_with_muscle
        return flattened

    def get_gym_database(self) -> Dict:
        """Get flattened gym database (loads if not already loaded). Prefers exercises.csv."""
        if self.gym_db is None:
            csv_path = getattr(Config, "EXERCISES_CSV_PATH", None)
            if csv_path and os.path.isfile(csv_path):
                self.gym_db = self._load_and_flatten_csv()
            else:
                raw_gym_db = self.load_gym_database()
                if raw_gym_db:
                    self.gym_db = self.flatten_gym_database(raw_gym_db)
                else:
                    self.gym_db = {}
        return self.gym_db


def _parse_json_list(value: Any) -> List[str]:
    """Parse a CSV cell that may contain a JSON list of strings."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if x]
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return [str(x).strip() for x in data if x] if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []
