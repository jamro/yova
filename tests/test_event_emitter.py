"""Tests for the EventEmitter class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from voice_command_station.core.event_emitter import EventEmitter


class TestEventEmitter:
    """Test cases for the EventEmitter class."""

    def test_init_without_logger(self):
        """Test EventEmitter initialization without logger."""
        emitter = EventEmitter()
        assert emitter._event_listeners == {}
        assert emitter.logger is None

    def test_init_with_logger(self):
        """Test EventEmitter initialization with logger."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        assert emitter._event_listeners == {}
        assert emitter.logger == mock_logger

    def test_add_event_listener_new_event_type(self):
        """Test adding a listener for a new event type."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        
        assert "test_event" in emitter._event_listeners
        assert len(emitter._event_listeners["test_event"]) == 1
        assert emitter._event_listeners["test_event"][0] == listener

    def test_add_event_listener_existing_event_type(self):
        """Test adding a listener for an existing event type."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        emitter.add_event_listener("test_event", listener1)
        emitter.add_event_listener("test_event", listener2)
        
        assert len(emitter._event_listeners["test_event"]) == 2
        assert listener1 in emitter._event_listeners["test_event"]
        assert listener2 in emitter._event_listeners["test_event"]

    def test_add_event_listener_with_logger(self):
        """Test adding a listener with logger enabled."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        
        mock_logger.debug.assert_called_once_with("Added event listener for 'test_event'")

    def test_remove_event_listener_existing(self):
        """Test removing an existing event listener."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        emitter.remove_event_listener("test_event", listener)
        
        # The event type key remains but the list is empty
        assert "test_event" in emitter._event_listeners
        assert len(emitter._event_listeners["test_event"]) == 0

    def test_remove_event_listener_nonexistent_event(self):
        """Test removing a listener from a non-existent event type."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        # Should not raise an exception
        emitter.remove_event_listener("nonexistent", listener)

    def test_remove_event_listener_nonexistent_listener(self):
        """Test removing a non-existent listener."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        emitter.add_event_listener("test_event", listener1)
        emitter.remove_event_listener("test_event", listener2)
        
        # listener1 should still be there
        assert len(emitter._event_listeners["test_event"]) == 1
        assert listener1 in emitter._event_listeners["test_event"]

    def test_remove_event_listener_with_logger(self):
        """Test removing a listener with logger enabled."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        emitter.remove_event_listener("test_event", listener)
        
        mock_logger.debug.assert_any_call("Removed event listener for 'test_event'")

    def test_clear_event_listeners_specific_event(self):
        """Test clearing listeners for a specific event type."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        emitter.add_event_listener("event1", listener1)
        emitter.add_event_listener("event2", listener2)
        
        emitter.clear_event_listeners("event1")
        
        # The event type key remains but the list is empty
        assert "event1" in emitter._event_listeners
        assert len(emitter._event_listeners["event1"]) == 0
        assert "event2" in emitter._event_listeners
        assert len(emitter._event_listeners["event2"]) == 1

    def test_clear_event_listeners_all(self):
        """Test clearing all event listeners."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        emitter.add_event_listener("event1", listener1)
        emitter.add_event_listener("event2", listener2)
        
        emitter.clear_event_listeners()
        
        assert emitter._event_listeners == {}

    def test_clear_event_listeners_with_logger(self):
        """Test clearing listeners with logger enabled."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        emitter.clear_event_listeners("test_event")
        
        mock_logger.debug.assert_any_call("Cleared event listeners for 'test_event'")

    def test_clear_all_event_listeners_with_logger(self):
        """Test clearing all listeners with logger enabled."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        emitter.clear_event_listeners()
        
        mock_logger.debug.assert_any_call("Cleared all event listeners")

    @pytest.mark.asyncio
    async def test_emit_event_with_listeners(self):
        """Test emitting an event to registered listeners."""
        emitter = EventEmitter()
        listener = AsyncMock()
        test_data = {"key": "value"}
        
        emitter.add_event_listener("test_event", listener)
        await emitter.emit_event("test_event", test_data)
        
        listener.assert_called_once_with(test_data)

    @pytest.mark.asyncio
    async def test_emit_event_no_listeners(self):
        """Test emitting an event with no registered listeners."""
        emitter = EventEmitter()
        
        # Should not raise an exception
        await emitter.emit_event("nonexistent", {"data": "test"})

    @pytest.mark.asyncio
    async def test_emit_event_multiple_listeners(self):
        """Test emitting an event to multiple listeners."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        test_data = {"key": "value"}
        
        emitter.add_event_listener("test_event", listener1)
        emitter.add_event_listener("test_event", listener2)
        
        await emitter.emit_event("test_event", test_data)
        
        listener1.assert_called_once_with(test_data)
        listener2.assert_called_once_with(test_data)

    @pytest.mark.asyncio
    async def test_emit_event_listener_exception(self):
        """Test emitting an event when a listener raises an exception."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        
        async def failing_listener(data):
            raise ValueError("Test exception")
        
        emitter.add_event_listener("test_event", failing_listener)
        
        # Should not raise an exception, should log the error
        await emitter.emit_event("test_event", {"data": "test"})
        
        mock_logger.error.assert_called_once()
        assert "Error in event listener for 'test_event'" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_emit_event_listener_exception_no_logger(self):
        """Test emitting an event when a listener raises an exception without logger."""
        emitter = EventEmitter()
        
        async def failing_listener(data):
            raise ValueError("Test exception")
        
        emitter.add_event_listener("test_event", failing_listener)
        
        # Should not raise an exception
        await emitter.emit_event("test_event", {"data": "test"})

    def test_has_listeners_with_listeners(self):
        """Test has_listeners when listeners exist."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        
        assert emitter.has_listeners("test_event") is True

    def test_has_listeners_no_listeners(self):
        """Test has_listeners when no listeners exist."""
        emitter = EventEmitter()
        
        assert emitter.has_listeners("test_event") is False

    def test_has_listeners_after_removal(self):
        """Test has_listeners after removing all listeners."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("test_event", listener)
        emitter.remove_event_listener("test_event", listener)
        
        assert emitter.has_listeners("test_event") is False

    def test_get_listener_count_with_listeners(self):
        """Test get_listener_count when listeners exist."""
        emitter = EventEmitter()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        emitter.add_event_listener("test_event", listener1)
        emitter.add_event_listener("test_event", listener2)
        
        assert emitter.get_listener_count("test_event") == 2

    def test_get_listener_count_no_listeners(self):
        """Test get_listener_count when no listeners exist."""
        emitter = EventEmitter()
        
        assert emitter.get_listener_count("test_event") == 0

    def test_get_all_event_types_empty(self):
        """Test get_all_event_types when no events have listeners."""
        emitter = EventEmitter()
        
        assert emitter.get_all_event_types() == []

    def test_get_all_event_types_with_events(self):
        """Test get_all_event_types when events have listeners."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("event1", listener)
        emitter.add_event_listener("event2", listener)
        
        event_types = emitter.get_all_event_types()
        assert len(event_types) == 2
        assert "event1" in event_types
        assert "event2" in event_types

    def test_get_all_event_types_after_removal(self):
        """Test get_all_event_types after removing all listeners for an event."""
        emitter = EventEmitter()
        listener = AsyncMock()
        
        emitter.add_event_listener("event1", listener)
        emitter.add_event_listener("event2", listener)
        emitter.clear_event_listeners("event1")
        
        event_types = emitter.get_all_event_types()
        # Both event types remain in the dictionary even after clearing listeners
        assert len(event_types) == 2
        assert "event1" in event_types
        assert "event2" in event_types


if __name__ == "__main__":
    pytest.main([__file__]) 