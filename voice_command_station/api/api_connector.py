from abc import ABC, abstractmethod
from typing import Any
from ..core.event_source import EventSource


class ApiConnector(EventSource):
    
    """
    Abstract interface for API connectors that can configure the API connector.
    
    Args:
        config: The configuration for the API connector
    """
    @abstractmethod
    async def configure(self, config: Any) -> None:
        """
        Configure the API connector.
        """
        pass


    """
    Abstract interface for API connectors that can connect to external services
    and send messages while also emitting events.
    
    This interface emits the following events:
    - message_chunk: Emitted when a partial message response is received
      Event data: {"id": str, "text": str} where id is a unique message identifier
    - message_completed: Emitted when a complete message response is received
      Event data: {"id": str, "text": str} where id is the same as the corresponding message_chunk events
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the API service.
        
        Raises:
            ConnectionError: If connection cannot be established
        """
        pass
    
    @abstractmethod
    async def send_message(self, text: str) -> Any:
        """
        Send a text message to the API service.
        
        Args:
            text: The message text to send
            
        Returns:
            Response from the API service
            
        Raises:
            ConnectionError: If not connected
            ValueError: If text is empty or invalid
        """
        pass
