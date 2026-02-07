"""
Gym Handler
Handles gym workout logging intents
"""

from datetime import datetime
from typing import Dict, Optional

from supabase import Client

from core.context import ConversationContext
from data import GymRepository
from handlers.base_handler import BaseHandler


class GymHandler(BaseHandler):
    """Handles gym workout logging"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.gym_repo = GymRepository(supabase)
    
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle gym workout logging"""
        # Parse workout from message
        workout_data = self.parser.parse_gym_workout(message)
        
        if not workout_data:
            return self.formatter.format_error("I couldn't parse that. Try something like 'bench press 135x5'")
        
        # Create gym log
        try:
            exercises = workout_data.get('exercises', [])
            if not exercises:
                return self.formatter.format_error("No exercises in that — try naming the exercise and sets, e.g. 'bench press 135x5'")
            
            # Log each exercise (repo expects: exercise, sets, reps, weight, notes)
            logged_exercises = []
            for exercise in exercises:
                exercise_name = (exercise.get('name') or '').strip() or 'exercise'
                sets_list = exercise.get('sets') or []
                sets_count = len(sets_list) if isinstance(sets_list, list) else (int(sets_list) if sets_list else 1)
                sets_count = max(1, sets_count)  # DB CHECK sets > 0
                first_set = sets_list[0] if sets_list and isinstance(sets_list, list) else {}
                reps_val = first_set.get('reps')
                weight_val = first_set.get('weight')
                notes = (workout_data.get('muscle_group') or '').strip() or None
                reps_int = int(reps_val) if reps_val is not None else None
                if reps_int is not None and reps_int <= 0:
                    reps_int = None
                weight_num = float(weight_val) if weight_val is not None else None
                if weight_num is not None and weight_num < 0:
                    weight_num = None

                created = self.gym_repo.create_gym_log(
                    user_id=user_id,
                    exercise=exercise_name,
                    sets=sets_count,
                    reps=reps_int,
                    weight=weight_num,
                    notes=notes
                )
                
                if not created:
                    print(f"Warning: create_gym_log returned None/empty for user {user_id}, exercise {exercise_name}")
                
                logged_exercises.append(exercise_name)
            
            # Invalidate context cache
            context.invalidate_cache()
            
            # Format response
            response = f"Got it — logged workout: {', '.join(logged_exercises)}"
            
            # Get today's summary
            today_summary = context.get_today_summary()
            if today_summary['gym']['count'] > 0:
                response += f"\nToday: {today_summary['gym']['count']} workout(s)"
            
            return response
            
        except Exception as e:
            print(f"Error logging workout: {e}")
            import traceback
            traceback.print_exc()
            return self.formatter.format_error("Couldn't save that workout")
