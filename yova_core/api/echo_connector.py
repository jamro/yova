import uuid
from .api_connector import ApiConnector
from yova_core.core.logging_utils import get_clean_logger
from yova_core.core.event_emitter import EventEmitter
from typing import Callable, Any, Awaitable

class EchoConnector(ApiConnector):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = get_clean_logger("echo_connector", logger)
        self.event_emitter = EventEmitter(logger=logger)

    async def configure(self, config: Any):
        self.logger.debug(f"EchoConnector: Configuring with config: {config}")
        pass

    async def connect(self):
        pass

    async def send_message(self, text: str):
        self.logger.debug(f"EchoConnector: Sending message: {text}")
        
        # Generate unique message ID for correlation
        message_id = str(uuid.uuid4())
        
        # Emit chunk event with ID and text
        chunk_data = {"id": message_id, "text": text}
        await self.event_emitter.emit_event("message_chunk", chunk_data)
        
        # Emit completion event with same ID and text
        completion_data = {"id": message_id, "text": text}
        await self.event_emitter.emit_event("message_completed", completion_data)
    
    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        self.event_emitter.add_event_listener(event_type, listener)

    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        self.event_emitter.remove_event_listener(event_type, listener)

    def clear_event_listeners(self, event_type: str = None):
        self.event_emitter.clear_event_listeners(event_type)
      