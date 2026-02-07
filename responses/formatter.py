"""
Response Formatter
Formats responses for SMS with proper length limits.
Greeting and fallback copy live here; recognition is done by NLP (intent classifier).
"""

from typing import Optional


class ResponseFormatter:
    """Formats responses for SMS"""
    
    # SMS character limits
    SMS_LENGTH_LIMIT = 1600  # Twilio supports up to 1600 chars
    
    def format_success(self, message: str) -> str:
        """Format a success message"""
        return f"✓ {message}"
    
    def format_error(self, message: Optional[str] = None) -> str:
        """Format an error message"""
        if message:
            return f"Something went wrong: {message}"
        return "Sorry, I couldn't do that. Try again in a sec?"
    
    def format_greeting(self) -> str:
        """Friendly reply when NLP classifies intent as greeting."""
        return (
            "Hey! Good to hear from you. "
            "You can ask me to log food, water, workouts, or set reminders—just say it in your own words."
        )
    
    def format_chitchat(self) -> str:
        """Friendly reply when NLP classifies intent as chitchat/off-topic (no command list)."""
        return (
            "I'm not sure I can help with that—but I'm here for food, water, workouts, and reminders. "
            "Just tell me in your own words and we're good."
        )
    
    def format_fallback(self, message: str) -> str:
        """Format a fallback response for unknown messages (friendly, open invite)."""
        return (
            "I'm not sure what you meant—but I'm here to help. "
            "You can log food, water, workouts, or set reminders. Just tell me in plain English, like \"ate a quesadilla\" or \"remind me to call Mom at 5.\""
        )
    
    def format_list(self, items: list, title: Optional[str] = None) -> str:
        """Format a list of items"""
        if not items:
            return "Nothing there yet."
        
        lines = []
        if title:
            lines.append(title)
        
        for i, item in enumerate(items[:10], 1):  # Limit to 10 items
            lines.append(f"{i}. {item}")
        
        if len(items) > 10:
            lines.append(f"... and {len(items) - 10} more")
        
        return "\n".join(lines)
    
    def truncate(self, message: str, max_length: Optional[int] = None) -> str:
        """Truncate message to fit SMS limits"""
        if max_length is None:
            max_length = self.SMS_LENGTH_LIMIT
        
        if len(message) <= max_length:
            return message
        
        # Truncate and add ellipsis
        return message[:max_length - 3] + "..."
    
    def format_stats(self, stats: dict) -> str:
        """Format statistics"""
        lines = []
        
        if 'food' in stats:
            food = stats['food']
            lines.append(f"Food: {food.get('count', 0)} items, {food.get('calories', 0)} cal")
        
        if 'water' in stats:
            water = stats['water']
            lines.append(f"Water: {water.get('liters', 0):.1f}L")
        
        if 'gym' in stats:
            gym = stats['gym']
            lines.append(f"Workouts: {gym.get('count', 0)}")
        
        return "\n".join(lines) if lines else "Nothing for today yet — start whenever you're ready!"
