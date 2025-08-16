from typing import Dict, List, Callable, Any, Awaitable
from abc import ABC, abstractmethod

class EventSource(ABC):
    """
    Abstract interface for components that emit events.
    This provides a clean contract for event-emitting functionality.
    """
    
    @abstractmethod
    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """
        Add an event listener for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            listener: Async function to call when the event occurs
        """
        pass
    
    @abstractmethod
    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """
        Remove an event listener for a specific event type.
        
        Args:
            event_type: The type of event to remove the listener from
            listener: The specific listener function to remove
        """
        pass
    
    @abstractmethod
    def clear_event_listeners(self, event_type: str = None):
        """
        Clear all event listeners or listeners for a specific event type.
        
        Args:
            event_type: Optional specific event type to clear. If None, clears all events.
        """
        pass
    