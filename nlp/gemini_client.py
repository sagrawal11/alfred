"""
Gemini API Client
Handles all communication with Google Gemini API
"""

import os
import re
import time
from typing import Optional

# Try new SDK first (google-genai), fallback to old deprecated SDK
try:
    from google import genai as google_genai
    NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai
        NEW_SDK = False
        import warnings
        warnings.warn(
            "Using deprecated 'google.generativeai' package. "
            "Please install 'google-genai' instead: pip install google-genai",
            DeprecationWarning,
            stacklevel=2
        )
    except ImportError:
        raise ImportError(
            "Neither 'google-genai' nor 'google-generativeai' is installed. "
            "Please install one: pip install google-genai"
        )


class GeminiClient:
    """Client for Google Gemini API with rate limiting and error handling"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to GEMINI_MODEL env var or 'gemini-2.5-flash')
        """
        api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        
        if NEW_SDK:
            self.client = google_genai.Client(api_key=api_key)
            print(f"Gemini client loaded (new SDK - {self.model_name})")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini model loaded (old SDK - {self.model_name})")
        
        self.last_request_time = 0
        
        # Set rate limits based on model
        if 'gemma' in self.model_name.lower():
            self.min_request_interval = 2
            print(f"Using Gemma rate limits: 30 req/min, 14.4k req/day")
        else:
            self.min_request_interval = 12
            print(f"Using Gemini rate limits: 5 req/min, 20 req/day (free tier)")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            print(f"Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def generate_content(self, prompt: str, system_prompt: Optional[str] = None, 
                        is_retry: bool = False) -> str:
        """
        Generate content using Gemini API
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            is_retry: Whether this is a retry attempt (skips rate limit)
            
        Returns:
            Generated text response
        """
        if not is_retry:
            self._rate_limit()
        
        try:
            if NEW_SDK:
                # New SDK (google-genai)
                # Build prompt with optional system prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                else:
                    full_prompt = prompt
                
                # Generate content using new SDK API
                # The new SDK API may vary, try multiple approaches
                try:
                    # Try the simpler API first (if it accepts string directly)
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=full_prompt
                    )
                except (TypeError, AttributeError):
                    # If that fails, try with contents as list
                    contents = [{"role": "user", "parts": [{"text": full_prompt}]}]
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents
                    )
                
                # Extract text from response (new SDK structure)
                if hasattr(response, 'text'):
                    return response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content'):
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            return candidate.content.parts[0].text.strip()
                        elif hasattr(candidate.content, 'text'):
                            return candidate.content.text.strip()
                return ""
            else:
                # Old SDK (google.generativeai) - deprecated
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
                    return self.generate_content(prompt, system_prompt, is_retry=True)
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
