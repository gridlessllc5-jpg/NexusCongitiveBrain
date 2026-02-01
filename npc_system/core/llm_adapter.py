"""
LLM Adapter - Replaces emergentintegrations with direct OpenAI SDK
This module provides a drop-in replacement for the emergentintegrations.llm.chat module
"""
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Support both old and new env var names
def get_api_key() -> str:
    """Get OpenAI API key from environment (supports legacy EMERGENT_LLM_KEY)"""
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise ValueError("No API key found. Set OPENAI_API_KEY or EMERGENT_LLM_KEY")
    return key


@dataclass
class UserMessage:
    """Compatible with emergentintegrations.llm.chat.UserMessage"""
    content: str = ""
    role: str = "user"
    text: str = ""  # Alias for content (Emergent compatibility)
    
    def __post_init__(self):
        # Support both 'text' and 'content' attributes
        if self.text and not self.content:
            self.content = self.text
        elif self.content and not self.text:
            self.text = self.content


class LlmChat:
    """
    Drop-in replacement for emergentintegrations.llm.chat.LlmChat
    Uses OpenAI SDK directly for Cloudflare Workers compatibility
    """
    
    # Model mapping from Emergent names to OpenAI
    MODEL_MAP = {
        "gpt-5.2": "gpt-4o",        # Map to latest available model
        "gpt-5": "gpt-4o",
        "gpt-4.5": "gpt-4o",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4": "gpt-4",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    }
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        system_message: str = ""
    ):
        self.api_key = api_key or get_api_key()
        self.session_id = session_id
        self.system_message = system_message
        self.model = "gpt-4o"  # Default model
        self.messages: List[Dict[str, str]] = []
        
        # Initialize OpenAI client
        self._client = OpenAI(api_key=self.api_key)
        self._async_client = AsyncOpenAI(api_key=self.api_key)
        
        # Add system message if provided
        if system_message:
            self.messages.append({
                "role": "system",
                "content": system_message
            })
    
    def with_model(self, provider: str, model: str) -> 'LlmChat':
        """Set the model to use (compatible with Emergent API)"""
        # Map Emergent model names to OpenAI equivalents
        if model in self.MODEL_MAP:
            self.model = self.MODEL_MAP[model]
        else:
            self.model = model
        return self
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history"""
        self.messages.append({"role": role, "content": content})
    
    async def send_message_async(self, message: str) -> str:
        """Send a message asynchronously and get the response"""
        self.add_message("user", message)
        
        try:
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            assistant_message = response.choices[0].message.content
            self.add_message("assistant", assistant_message)
            return assistant_message
            
        except Exception as e:
            raise Exception(f"LLM API Error: {str(e)}")
    
    def send_message(self, message: str) -> str:
        """Send a message synchronously and get the response"""
        self.add_message("user", message)
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            assistant_message = response.choices[0].message.content
            self.add_message("assistant", assistant_message)
            return assistant_message
            
        except Exception as e:
            raise Exception(f"LLM API Error: {str(e)}")
    
    async def send_user_message(self, user_message: UserMessage) -> str:
        """Send a UserMessage object (Emergent compatibility)"""
        return await self.send_message_async(user_message.content)
    
    def reset_conversation(self):
        """Clear conversation history but keep system message"""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []


class OpenAISpeechToText:
    """
    Drop-in replacement for emergentintegrations.llm.openai.OpenAISpeechToText
    Uses OpenAI Whisper API for speech-to-text
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self._client = OpenAI(api_key=self.api_key)
        self._async_client = AsyncOpenAI(api_key=self.api_key)
    
    async def transcribe_async(
        self, 
        audio_data: bytes,
        language: str = "en",
        response_format: str = "text"
    ) -> str:
        """Transcribe audio data to text asynchronously"""
        import io
        
        # Create a file-like object from audio bytes
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.webm"  # OpenAI needs a filename with extension
        
        try:
            response = await self._async_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format=response_format
            )
            
            if response_format == "text":
                return response
            return response.text
            
        except Exception as e:
            raise Exception(f"Speech-to-Text Error: {str(e)}")
    
    def transcribe(
        self, 
        audio_data: bytes,
        language: str = "en",
        response_format: str = "text"
    ) -> str:
        """Transcribe audio data to text synchronously"""
        import io
        
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.webm"
        
        try:
            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format=response_format
            )
            
            if response_format == "text":
                return response
            return response.text
            
        except Exception as e:
            raise Exception(f"Speech-to-Text Error: {str(e)}")


# Convenience function for simple one-off completions
async def complete_async(
    prompt: str,
    system_message: str = "",
    model: str = "gpt-4o",
    api_key: Optional[str] = None
) -> str:
    """Simple async completion without maintaining conversation"""
    client = AsyncOpenAI(api_key=api_key or get_api_key())
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7
    )
    
    return response.choices[0].message.content
