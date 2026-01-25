"""
Todo Handler
Handles todo, reminder, and assignment intents
"""

from typing import Dict, Optional
from datetime import datetime
from supabase import Client

from handlers.base_handler import BaseHandler
from core.context import ConversationContext
from data import TodoRepository, AssignmentRepository
from typing import Optional


class TodoHandler(BaseHandler):
    """Handles todos, reminders, and assignments"""
    
    def __init__(self, supabase: Client, parser, formatter):
        super().__init__(supabase, parser, formatter)
        self.todo_repo = TodoRepository(supabase)
        self.assignment_repo = AssignmentRepository(supabase)
    
    def handle(self, message: str, intent: str, entities: Dict, 
               user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle todo/reminder/assignment creation"""
        if intent == 'reminder_set':
            return self._handle_reminder(message, user_id, context)
        elif intent == 'assignment_add':
            return self._handle_assignment(message, user_id, context)
        else:  # todo_add
            return self._handle_todo(message, user_id, context)
    
    def _handle_todo(self, message: str, user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle todo creation"""
        # Parse todo from message (simple text extraction)
        todo_text = message.strip()
        
        # Remove common prefixes
        prefixes = ['todo:', 'add todo:', 'remind me to', 'i need to', 'i should']
        for prefix in prefixes:
            if todo_text.lower().startswith(prefix):
                todo_text = todo_text[len(prefix):].strip()
        
        if not todo_text:
            return self.formatter.format_error("What do you need to do?")
        
        try:
            created = self.todo_repo.create_todo(
                user_id=user_id,
                content=todo_text,
                due_date=None  # No due date for simple todos
            )
            
            context.invalidate_cache()
            
            return f"✓ Added todo: {todo_text}"
            
        except Exception as e:
            print(f"Error creating todo: {e}")
            return self.formatter.format_error("Error saving todo")
    
    def _handle_reminder(self, message: str, user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle reminder creation"""
        # Parse reminder from message
        reminder_data = self.parser.parse_reminder(message)
        
        if not reminder_data:
            return self.formatter.format_error("Couldn't parse reminder. Try: 'remind me to call mom at 5pm'")
        
        content = reminder_data.get('content', '')
        due_date = reminder_data.get('due_date')
        
        if not content:
            return self.formatter.format_error("What should I remind you about?")
        
        try:
            created = self.todo_repo.create_todo(
                user_id=user_id,
                content=content,
                due_date=due_date
            )
            
            context.invalidate_cache()
            
            response = f"✓ Reminder set: {content}"
            if due_date:
                due_str = datetime.fromisoformat(due_date) if isinstance(due_date, str) else due_date
                response += f" at {due_str.strftime('%I:%M %p')}"
            
            return response
            
        except Exception as e:
            print(f"Error creating reminder: {e}")
            return self.formatter.format_error("Error saving reminder")
    
    def _handle_assignment(self, message: str, user_id: int, context: ConversationContext) -> Optional[str]:
        """Handle assignment creation"""
        # Parse assignment from message
        assignment_data = self.parser.parse_assignment(message)
        
        if not assignment_data:
            return self.formatter.format_error("Couldn't parse assignment. Try: 'CS101 homework due Friday'")
        
        class_name = assignment_data.get('class_name', '')
        assignment_name = assignment_data.get('assignment_name', '')
        due_date = assignment_data.get('due_date')
        
        if not class_name or not assignment_name:
            return self.formatter.format_error("Need class name and assignment name")
        
        try:
            created = self.assignment_repo.create_assignment(
                user_id=user_id,
                class_name=class_name,
                assignment_name=assignment_name,
                due_date=due_date
            )
            
            context.invalidate_cache()
            
            response = f"✓ Added assignment: {class_name} - {assignment_name}"
            if due_date:
                due_str = datetime.fromisoformat(due_date) if isinstance(due_date, str) else due_date
                response += f" (due {due_str.strftime('%b %d')})"
            
            return response
            
        except Exception as e:
            print(f"Error creating assignment: {e}")
            return self.formatter.format_error("Error saving assignment")
