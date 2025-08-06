from typing import Dict, List, Callable, Any, Awaitable

class EventEmitter:
    """
    A reusable event emitter class that provides event listener functionality.
    This class eliminates code duplication across components that need event handling.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the EventEmitter.
        
        Args:
            logger: Optional logger instance for debugging. If None, no logging will occur.
        """
        # Event listeners: {event_type: [listener_functions]}
        self._event_listeners: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {}
        self.logger = logger
    
    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """
        Add an event listener for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            listener: Async function to call when the event occurs
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(listener)
        if self.logger:
            self.logger.debug(f"Added event listener for '{event_type}'")
    
    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """
        Remove an event listener for a specific event type.
        
        Args:
            event_type: The type of event to remove the listener from
            listener: The specific listener function to remove
        """
        if event_type in self._event_listeners and listener in self._event_listeners[event_type]:
            self._event_listeners[event_type].remove(listener)
            if self.logger:
                self.logger.debug(f"Removed event listener for '{event_type}'")
    
    def clear_event_listeners(self, event_type: str = None):
        """
        Clear all event listeners or listeners for a specific event type.
        
        Args:
            event_type: Optional specific event type to clear. If None, clears all listeners.
        """
        if event_type is None:
            self._event_listeners.clear()
            if self.logger:
                self.logger.debug("Cleared all event listeners")
        elif event_type in self._event_listeners:
            self._event_listeners[event_type].clear()
            if self.logger:
                self.logger.debug(f"Cleared event listeners for '{event_type}'")
    
    async def emit_event(self, event_type: str, data: Any):
        """
        Emit an event to all registered listeners.
        
        Args:
            event_type: The type of event being emitted
            data: The data to pass to the event listeners
        """
        if event_type in self._event_listeners:
            for listener in self._event_listeners[event_type]:
                try:
                    await listener(data)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in event listener for '{event_type}': {e}")
                        import traceback
                        traceback.print_exc()
    
    def has_listeners(self, event_type: str) -> bool:
        """
        Check if there are any listeners for a specific event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if there are listeners for the event type, False otherwise
        """
        return event_type in self._event_listeners and len(self._event_listeners[event_type]) > 0
    
    def get_listener_count(self, event_type: str) -> int:
        """
        Get the number of listeners for a specific event type.
        
        Args:
            event_type: The event type to count listeners for
            
        Returns:
            The number of listeners for the event type
        """
        if event_type in self._event_listeners:
            return len(self._event_listeners[event_type])
        return 0
    
    def get_all_event_types(self) -> List[str]:
        """
        Get a list of all event types that have listeners.
        
        Returns:
            List of event type strings
        """
        return list(self._event_listeners.keys()) 