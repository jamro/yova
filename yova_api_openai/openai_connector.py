import os
import asyncio
import uuid
from typing import Any, Optional
from openai import AsyncOpenAI
from yova_shared.api import ApiConnector
from yova_shared import get_clean_logger
from yova_shared import EventEmitter
from .conversation_history import ConversationHistory
import base64
import random

# Supported audio formats and their MIME types
SUPPORTED_FORMATS = {
    'wav': 'audio/wav',
    'mp3': 'audio/mpeg',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac',
    'aac': 'audio/aac',
    'm4a': 'audio/mp4',
    'wma': 'audio/x-ms-wma'
}

def get_file_format(file_path):
    """Extract file format from file path"""
    _, ext = os.path.splitext(file_path)
    return ext.lower().lstrip('.')
    
def is_format_supported(format_ext):
    """Check if the audio format is supported"""
    return format_ext in SUPPORTED_FORMATS

class OpenAIConnector(ApiConnector):
    def __init__(self, logger=None, max_history_messages: int = 50, max_history_tokens: int = 10000):
        super().__init__()
        self.logger = get_clean_logger("openai_connector", logger)
        self.event_emitter = EventEmitter(logger=logger)
        self.client: Optional[AsyncOpenAI] = None
        self.api_key: Optional[str] = None
        self.model: str = "gpt-4o"
        self.system_prompt: str = "You are a helpful AI assistant. Always begin your response with a natural, human-like short phrase of 1-3 words (e.g., 'Sounds good,' 'Got it,' 'Absolutely', 'No problem'). After that, continue with your full answer in a helpful and conversational tone."
        self.max_tokens: int = 1000
        self.temperature: float = 0.8
        self.is_connected: bool = False
        
        # Initialize conversation history
        self.conversation_history = ConversationHistory(
            max_messages=max_history_messages,
            max_tokens=max_history_tokens,
            logger=logger
        )

    async def configure(self, config: Any):
        """Configure the OpenAI connector with API key and optional parameters."""
        self.logger.debug(f"OpenAIConnector: Configuring with config: {config}")
        
        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it in config or OPENAI_API_KEY environment variable.")
        
        # Set optional configuration parameters
        self.model = config.get("model", self.model)
        self.system_prompt = config.get("system_prompt", self.system_prompt)
        self.max_tokens = config.get("max_tokens", self.max_tokens)
        self.temperature = config.get("temperature", self.temperature)
        
        # Configure conversation history if specified
        if "max_history_messages" in config:
            self.conversation_history.max_messages = config["max_history_messages"]
        if "max_history_tokens" in config:
            self.conversation_history.max_tokens = config["max_history_tokens"]
        
        self.logger.info(f"OpenAIConnector: Configured with model {self.model}")

    async def connect(self):
        """Initialize the OpenAI client."""
        if not self.api_key:
            raise ConnectionError("OpenAI API key not configured. Call configure() first.")
        
        try:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.is_connected = True
            self.logger.info("OpenAIConnector: Successfully connected to OpenAI API")
        except Exception as e:
            self.logger.error(f"OpenAIConnector: Failed to connect to OpenAI API: {e}")
            raise ConnectionError(f"Failed to connect to OpenAI API: {e}")

    async def send_message(self, text: str):
        """Send a message to OpenAI and stream the response chunk by chunk."""
        if not self.is_connected or not self.client:
            raise ConnectionError("Not connected to OpenAI API. Call connect() first.")
        
        if not text or not text.strip():
            return ""
        
        self.logger.debug(f"OpenAIConnector: Sending message: {text}")
        
        # Generate unique message ID for correlation
        message_id = str(uuid.uuid4())

        # send hmmm sound to increase user confidence
        chunk_data = {"id": message_id, "text": self.get_hmmm_sound_base64()}
        await self.event_emitter.emit_event("message_chunk", chunk_data)
        self.logger.debug(f"OpenAIConnector: Emitted hmmm sound chunk: {chunk_data['text'][:20]}...")

        # Add user message to conversation history
        self.conversation_history.add_user_message(text, message_id)
        
        await self.event_emitter.emit_event("processing_started", {"id": message_id})

        try:
            # Get conversation history for context
            messages = self.conversation_history.get_messages_for_api(
                include_system=True,
                system_prompt=self.system_prompt
            )
            
            # Create the chat completion with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            full_response = ""
            
            # Process the streaming response
            first_chunk = True
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content

                    if first_chunk:
                        await self.event_emitter.emit_event("processing_completed", {"id": message_id})
                        first_chunk = False
                    
                    # Emit chunk event with ID and text
                    chunk_data = {"id": message_id, "text": content}
                    await self.event_emitter.emit_event("message_chunk", chunk_data)
                    self.logger.debug(f"OpenAIConnector: Emitted chunk: {chunk_data}")
            
            # Add assistant response to conversation history
            self.conversation_history.add_assistant_message(full_response, message_id)
            
            # Emit completion event with same ID and full text
            completion_data = {"id": message_id, "text": full_response}
            await self.event_emitter.emit_event("message_completed", completion_data)
            self.logger.debug(f"OpenAIConnector: Message completed, total response: {completion_data}")
            
            return full_response
            
        except Exception as e:
            self.logger.error(f"OpenAIConnector: Error sending message: {e}")
            raise ConnectionError(f"Failed to send message to OpenAI: {e}")

    def add_event_listener(self, event_type: str, listener):
        """Add an event listener for a specific event type."""
        self.event_emitter.add_event_listener(event_type, listener)

    def remove_event_listener(self, event_type: str, listener):
        """Remove an event listener for a specific event type."""
        self.event_emitter.remove_event_listener(event_type, listener)

    def clear_event_listeners(self, event_type: str = None):
        """Clear all event listeners or listeners for a specific event type."""
        self.event_emitter.clear_event_listeners(event_type)

    # Conversation history management methods
    def get_conversation_history(self) -> ConversationHistory:
        """Get the conversation history manager."""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clear all conversation history."""
        self.conversation_history.clear_history()
        self.logger.info("OpenAIConnector: Cleared conversation history")

    def get_conversation_statistics(self):
        """Get statistics about the current conversation."""
        return self.conversation_history.get_statistics()

    def export_conversation(self, format_type: str = "json") -> str:
        """Export conversation history in specified format."""
        return self.conversation_history.export_history(format_type) 
    
    def get_hmmm_sound_base64(self):
        # construct path to wav file using current file location and relative path to wav file
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yova_shared", "assets", f"hmmm_nova_{random.randint(1, 9)}.wav")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found!")

        format_ext = get_file_format(file_path)
        
        # Check if format is supported
        if not is_format_supported(format_ext):
            supported_formats = ', '.join(SUPPORTED_FORMATS.keys())
            raise ValueError(f"Unsupported audio format: {format_ext}. Supported formats: {supported_formats}")
        
        # Read the audio file as binary
        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Encode with base64
        base64_encoded = base64.b64encode(audio_data)
        base64_string = base64_encoded.decode('utf-8')
        
        # Create data URL with proper MIME type
        mime_type = SUPPORTED_FORMATS[format_ext]
        data_url = f"data:{mime_type};base64,{base64_string}"

        return data_url