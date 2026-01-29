"""
Intent Classifier
Classifies user messages into specific intents
"""

from typing import Dict, Optional
from .llm_types import LLMClient


class IntentClassifier:
    """Classifies user messages into intents"""
    
    # Valid intent types
    VALID_INTENTS = [
        'water_logging', 'food_logging', 'gym_workout', 'sleep_logging',
        'reminder_set', 'todo_add', 'assignment_add', 'water_goal_set',
        'stats_query', 'fact_storage', 'fact_query', 'task_complete',
        'vague_completion', 'what_should_i_do', 'food_suggestion',
        'undo_edit', 'confirmation', 'integration_manage', 'unknown'
    ]
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize intent classifier
        
        Args:
            llm_client: LLM client instance
        """
        self.client = llm_client
    
    def classify(self, message: str) -> str:
        """
        Classify the intent of a message
        
        Args:
            message: User message
            
        Returns:
            Intent name (one of VALID_INTENTS)
        """
        prompt = f"""Classify this SMS message into one of these intents:
- water_logging: User is logging water intake
- food_logging: User is logging food consumption. This includes ANY message that mentions eating food, such as: "ate", "just ate", "eating", "had", "consumed", "finished eating", "just finished eating", "just had", or any mention of food items, meals, snacks, restaurants, or dishes. Examples: "just ate a quesadilla", "ate sprout falafel wrap", "had a burger", "just finished eating pizza"
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
- integration_manage: User wants to manage integrations (e.g., "connect fitbit", "sync my calendar", "disconnect fitbit", "what integrations do I have", "list integrations")
- confirmation: User is confirming or denying something (e.g., "yes", "yep", "correct", "no", "nope", "that's right")
- unknown: Doesn't match any category

IMPORTANT: 
- If a message mentions a class name/number AND a due date, classify as "assignment_add" (e.g., "CS101 homework due Friday")
- If a message has BOTH a task/todo AND a time/date (e.g., "I need to call mama at 5pm tomorrow"), classify it as "reminder_set" because reminders are more specific than todos.

Message: "{message}"

Respond with ONLY the intent name, nothing else."""
        
        try:
            intent = self.client.generate_content(prompt).lower().strip()
            
            # Validate intent
            if intent in self.VALID_INTENTS:
                return intent
            else:
                # Try to extract intent from response
                for valid_intent in self.VALID_INTENTS:
                    if valid_intent in intent:
                        return valid_intent
                return 'unknown'
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return 'unknown'
    
    def guess_intent(self, message: str) -> Optional[Dict]:
        """
        Guess intent for vague messages (like "just finished", "done")
        Returns a list of likely intents with confidence scores
        
        Args:
            message: User message
            
        Returns:
            Dictionary with likely intents and confidence, or None if not vague
        """
        # Only process if message is vague
        vague_indicators = ['just finished', 'done', 'finished', 'all done', 'complete', 'completed']
        if not any(indicator in message.lower() for indicator in vague_indicators):
            return None
        
        prompt = f"""This message is vague/ambiguous: "{message}"

Based on context, what are the 3 most likely interpretations? Return JSON:
{{
  "interpretations": [
    {{"intent": "gym_workout", "description": "Finished a workout", "confidence": 0.8}},
    {{"intent": "food_logging", "description": "Finished eating a meal", "confidence": 0.7}},
    {{"intent": "task_complete", "description": "Completed a task", "confidence": 0.6}}
  ]
}}

Respond with ONLY valid JSON, no other text."""
        
        try:
            import json
            import re
            text = self.client.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except Exception as e:
            print(f"Error guessing intent: {e}")
            return None
