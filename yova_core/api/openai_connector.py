import os
import asyncio
import uuid
from typing import Any, Optional
from openai import AsyncOpenAI
from .api_connector import ApiConnector
from yova_core.core.logging_utils import get_clean_logger
from yova_core.core.event_emitter import EventEmitter


class OpenAIConnector(ApiConnector):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = get_clean_logger("openai_connector", logger)
        self.event_emitter = EventEmitter(logger=logger)
        self.client: Optional[AsyncOpenAI] = None
        self.api_key: Optional[str] = None
        self.model: str = "gpt-4o"
        self.system_prompt: str = "You are a helpful AI assistant."
        self.max_tokens: int = 1000
        self.temperature: float = 0.7
        self.is_connected: bool = False

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
            raise ValueError("Message text cannot be empty")
        
        self.logger.debug(f"OpenAIConnector: Sending message: {text}")
        
        # Generate unique message ID for correlation
        message_id = str(uuid.uuid4())
        
        try:
            # Create the chat completion with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            full_response = ""
            
            # Process the streaming response
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Emit chunk event with ID and text
                    chunk_data = {"id": message_id, "text": content}
                    await self.event_emitter.emit_event("message_chunk", chunk_data)
                    self.logger.debug(f"OpenAIConnector: Emitted chunk: {chunk_data}")
            
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