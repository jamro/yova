"""Tests for the EchoConnector class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from yova_shared.api.echo_connector import EchoConnector


class TestEchoConnector:
    """Test cases for the EchoConnector class."""

    def test_init_without_logger(self):
        """Test EchoConnector initialization without logger."""
        connector = EchoConnector()
        assert connector.logger is not None
        assert connector.event_emitter is not None
        assert connector.logger.name == "echo_connector"

    def test_init_with_logger(self):
        """Test EchoConnector initialization with custom logger."""
        mock_logger = Mock()
        connector = EchoConnector(logger=mock_logger)
        assert connector.logger == mock_logger
        assert connector.event_emitter is not None
        assert connector.event_emitter.logger == mock_logger

    @pytest.mark.asyncio
    async def test_configure(self):
        """Test EchoConnector configuration."""
        connector = EchoConnector()
        config = {"test": "config", "value": 123}
        
        # Should not raise any exception
        await connector.configure(config)
        
        # Verify logger was called with debug message
        # Note: We can't easily test the logger call without mocking it
        # since the logger is created internally

    @pytest.mark.asyncio
    async def test_configure_with_logger(self):
        """Test EchoConnector configuration with mocked logger."""
        mock_logger = Mock()
        connector = EchoConnector(logger=mock_logger)
        config = {"test": "config", "value": 123}
        
        await connector.configure(config)
        
        mock_logger.debug.assert_called_once_with(
            f"EchoConnector: Configuring with config: {config}"
        )

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test EchoConnector connection."""
        connector = EchoConnector()
        
        # Should not raise any exception
        await connector.connect()

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test EchoConnector send_message functionality."""
        connector = EchoConnector()
        test_message = "Hello, world!"
        
        # Mock the event emitter to capture emitted events
        mock_emit = AsyncMock()
        connector.event_emitter.emit_event = mock_emit
        
        await connector.send_message(test_message)
        
        # Verify both events were emitted
        assert mock_emit.call_count == 2
        
        # Check the calls were made with correct arguments
        calls = mock_emit.call_args_list
        assert calls[0][0][0] == "message_chunk"
        assert calls[0][0][1]["text"] == test_message
        assert "id" in calls[0][0][1]
        assert calls[1][0][0] == "message_completed"
        assert calls[1][0][1]["text"] == test_message
        assert "id" in calls[1][0][1]
        # Verify same ID for correlation
        assert calls[0][0][1]["id"] == calls[1][0][1]["id"]

    @pytest.mark.asyncio
    async def test_send_message_with_logger(self):
        """Test EchoConnector send_message with mocked logger."""
        mock_logger = Mock()
        connector = EchoConnector(logger=mock_logger)
        test_message = "Test message"
        
        # Mock the event emitter
        mock_emit = AsyncMock()
        connector.event_emitter.emit_event = mock_emit
        
        await connector.send_message(test_message)
        
        # Verify logger was called
        mock_logger.debug.assert_called_once_with(
            f"EchoConnector: Sending message: {test_message}"
        )
        
        # Verify events were emitted
        assert mock_emit.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_empty_string(self):
        """Test EchoConnector send_message with empty string."""
        connector = EchoConnector()
        test_message = ""
        
        # Mock the event emitter
        mock_emit = AsyncMock()
        connector.event_emitter.emit_event = mock_emit
        
        await connector.send_message(test_message)
        
        # Verify events were emitted with empty string
        assert mock_emit.call_count == 2
        calls = mock_emit.call_args_list
        assert calls[0][0][1]["text"] == ""
        assert "id" in calls[0][0][1]
        assert calls[1][0][1]["text"] == ""
        assert "id" in calls[1][0][1]
        # Verify same ID for correlation
        assert calls[0][0][1]["id"] == calls[1][0][1]["id"]

    @pytest.mark.asyncio
    async def test_send_message_special_characters(self):
        """Test EchoConnector send_message with special characters."""
        connector = EchoConnector()
        test_message = "Hello\nWorld\tTest\r\n"
        
        # Mock the event emitter
        mock_emit = AsyncMock()
        connector.event_emitter.emit_event = mock_emit
        
        await connector.send_message(test_message)
        
        # Verify events were emitted with the exact message
        assert mock_emit.call_count == 2
        calls = mock_emit.call_args_list
        assert calls[0][0][1]["text"] == test_message
        assert "id" in calls[0][0][1]
        assert calls[1][0][1]["text"] == test_message
        assert "id" in calls[1][0][1]
        # Verify same ID for correlation
        assert calls[0][0][1]["id"] == calls[1][0][1]["id"]

    def test_add_event_listener(self):
        """Test adding event listeners to EchoConnector."""
        connector = EchoConnector()
        listener = AsyncMock()
        
        connector.add_event_listener("test_event", listener)
        
        # Verify the listener was added to the event emitter
        assert connector.event_emitter.has_listeners("test_event")
        assert connector.event_emitter.get_listener_count("test_event") == 1

    def test_add_multiple_event_listeners(self):
        """Test adding multiple event listeners to EchoConnector."""
        connector = EchoConnector()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        connector.add_event_listener("test_event", listener1)
        connector.add_event_listener("test_event", listener2)
        
        # Verify both listeners were added
        assert connector.event_emitter.get_listener_count("test_event") == 2

    def test_remove_event_listener(self):
        """Test removing event listeners from EchoConnector."""
        connector = EchoConnector()
        listener = AsyncMock()
        
        connector.add_event_listener("test_event", listener)
        connector.remove_event_listener("test_event", listener)
        
        # Verify the listener was removed
        assert not connector.event_emitter.has_listeners("test_event")
        assert connector.event_emitter.get_listener_count("test_event") == 0

    def test_clear_event_listeners_specific_event(self):
        """Test clearing specific event listeners from EchoConnector."""
        connector = EchoConnector()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        connector.add_event_listener("event1", listener1)
        connector.add_event_listener("event2", listener2)
        
        connector.clear_event_listeners("event1")
        
        # Verify only event1 listeners were cleared
        assert not connector.event_emitter.has_listeners("event1")
        assert connector.event_emitter.has_listeners("event2")

    def test_clear_all_event_listeners(self):
        """Test clearing all event listeners from EchoConnector."""
        connector = EchoConnector()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        connector.add_event_listener("event1", listener1)
        connector.add_event_listener("event2", listener2)
        
        connector.clear_event_listeners()
        
        # Verify all listeners were cleared
        assert not connector.event_emitter.has_listeners("event1")
        assert not connector.event_emitter.has_listeners("event2")

    @pytest.mark.asyncio
    async def test_integration_send_message_with_listeners(self):
        """Test integration of send_message with actual event listeners."""
        connector = EchoConnector()
        received_chunks = []
        received_completions = []
        
        async def chunk_listener(data):
            received_chunks.append(data)
        
        async def completion_listener(data):
            received_completions.append(data)
        
        connector.add_event_listener("message_chunk", chunk_listener)
        connector.add_event_listener("message_completed", completion_listener)
        
        test_message = "Integration test message"
        await connector.send_message(test_message)
        
        # Verify listeners received the events
        assert len(received_chunks) == 1
        assert received_chunks[0]["text"] == test_message
        assert "id" in received_chunks[0]
        assert len(received_completions) == 1
        assert received_completions[0]["text"] == test_message
        assert "id" in received_completions[0]
        # Verify same ID for correlation
        assert received_chunks[0]["id"] == received_completions[0]["id"]

    @pytest.mark.asyncio
    async def test_multiple_send_messages(self):
        """Test sending multiple messages in sequence."""
        connector = EchoConnector()
        received_messages = []
        
        async def message_listener(data):
            received_messages.append(data)
        
        connector.add_event_listener("message_completed", message_listener)
        
        messages = ["First message", "Second message", "Third message"]
        
        for message in messages:
            await connector.send_message(message)
        
        # Verify all messages were received
        assert len(received_messages) == 3
        for i, message in enumerate(messages):
            assert received_messages[i]["text"] == message
            assert "id" in received_messages[i]

    @pytest.mark.asyncio
    async def test_send_message_with_failing_listener(self):
        """Test send_message behavior when a listener fails."""
        connector = EchoConnector()
        received_messages = []
        
        async def working_listener(data):
            received_messages.append(data)
        
        async def failing_listener(data):
            raise Exception("Listener failed")
        
        connector.add_event_listener("message_completed", working_listener)
        connector.add_event_listener("message_completed", failing_listener)
        
        test_message = "Test message"
        
        # Should not raise exception, but working listener should still receive the message
        await connector.send_message(test_message)
        
        assert len(received_messages) == 1
        assert received_messages[0]["text"] == test_message
        assert "id" in received_messages[0]

    def test_inheritance_from_api_connector(self):
        """Test that EchoConnector properly inherits from ApiConnector."""
        connector = EchoConnector()
        
        # Verify it's an instance of ApiConnector
        from yova_shared.api.api_connector import ApiConnector
        assert isinstance(connector, ApiConnector)

    def test_event_emitter_integration(self):
        """Test that EchoConnector properly integrates with EventEmitter."""
        connector = EchoConnector()
        
        # Verify event emitter is properly initialized
        assert connector.event_emitter is not None
        assert hasattr(connector.event_emitter, 'add_event_listener')
        assert hasattr(connector.event_emitter, 'remove_event_listener')
        assert hasattr(connector.event_emitter, 'clear_event_listeners')
        assert hasattr(connector.event_emitter, 'emit_event') 