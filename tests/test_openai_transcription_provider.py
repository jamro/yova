"""Tests for the OpenAiTranscriptionProvider class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider

class TestOpenAiTranscriptionProvider:
    """Test cases for the OpenAiTranscriptionProvider class."""
    
    def test_initialization_default_dependencies(self):
        """Test OpenAiTranscriptionProvider initialization with default dependencies."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        
        assert handler.api_key == "test_api_key"
        assert handler.websocket_uri == "wss://api.openai.com/v1/realtime"
        assert handler.websocket is None
        assert handler.session_id is None
        assert handler.logger is not None
        assert handler._logged_invalid_request is False
        assert handler.event_emitter is not None
    
    def test_initialization_with_injected_dependencies(self):
        """Test OpenAiTranscriptionProvider initialization with injected dependencies."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_websocket_connector = Mock()
        
        handler = OpenAiTranscriptionProvider(
            "test_api_key", 
            mock_logger, 
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector
        )
        
        assert handler._openai_client == mock_openai_client
        assert handler._websocket_connector == mock_websocket_connector
    
    def test_initialization_with_custom_websocket_uri(self):
        """Test OpenAiTranscriptionProvider initialization with custom WebSocket URI."""
        mock_logger = Mock()
        custom_uri = "wss://custom.example.com"
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, websocket_uri=custom_uri)
        assert handler.websocket_uri == custom_uri
    
    def test_add_event_listener(self):
        """Test adding an event listener."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        
        mock_listener = AsyncMock()
        handler.add_event_listener("test_event", mock_listener)
        
        # Verify the listener was added to the event emitter
        assert mock_listener in handler.event_emitter._event_listeners.get("test_event", [])
    
    def test_remove_event_listener(self):
        """Test removing an event listener."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        
        mock_listener = AsyncMock()
        handler.add_event_listener("test_event", mock_listener)
        handler.remove_event_listener("test_event", mock_listener)
        
        # Verify the listener was removed from the event emitter
        assert mock_listener not in handler.event_emitter._event_listeners.get("test_event", [])
    
    def test_clear_event_listeners(self):
        """Test clearing event listeners."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        
        mock_listener = AsyncMock()
        handler.add_event_listener("test_event", mock_listener)
        handler.clear_event_listeners("test_event")
        
        # Verify the listeners were cleared
        assert len(handler.event_emitter._event_listeners.get("test_event", [])) == 0
    
    @pytest.mark.asyncio
    async def test_create_transcription_session_success(self):
        """Test successful transcription session creation."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.client_secret = "test_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.return_value = mock_response
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, openai_client=mock_openai_client)
        
        result = await handler.create_transcription_session()
        
        assert result == "test_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_transcription_session_failure(self):
        """Test transcription session creation failure."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_openai_client.beta.realtime.transcription_sessions.create.side_effect = Exception("API Error")
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, openai_client=mock_openai_client)
        
        result = await handler.create_transcription_session()
        
        assert result is None
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_connect_websocket_success(self):
        """Test successful WebSocket connection."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        mock_websocket_connector = AsyncMock(return_value=mock_websocket)
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, websocket_connector=mock_websocket_connector)
        
        result = await handler.connect_websocket("test_secret")
        
        assert result is True
        assert handler.websocket == mock_websocket
        mock_websocket_connector.assert_called_once()
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self):
        """Test WebSocket connection failure."""
        mock_logger = Mock()
        mock_websocket_connector = AsyncMock(side_effect=Exception("Connection Error"))
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, websocket_connector=mock_websocket_connector)
        
        result = await handler.connect_websocket("test_secret")
        
        assert result is False
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_audio_data_success(self):
        """Test successful audio data sending."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = "test_session"
        
        # Use proper test audio data that's a multiple of 2 bytes (int16)
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes = 3 int16 values
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is True
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_audio_data_no_websocket(self):
        """Test audio data sending when WebSocket is not connected."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        
        # Use proper test audio data that's a multiple of 2 bytes (int16)
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes = 3 int16 values
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is False
        mock_logger.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_audio_data_connection_closed(self):
        """Test audio data sending when WebSocket connection is closed."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock(side_effect=Exception("Connection closed"))
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = "test_session"
        
        # Use proper test audio data that's a multiple of 2 bytes (int16)
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes = 3 int16 values
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is False
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_websocket_messages_session_created(self):
        """Test handling WebSocket message for session creation."""
        mock_logger = Mock()
        
        # Create a proper async iterator
        async def async_iter():
            yield '{"type": "transcription_session.created", "session": {"id": "test_session_id"}}'
        
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__ = lambda self: async_iter()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        assert handler.session_id == "test_session_id"
    
    @pytest.mark.asyncio
    async def test_handle_websocket_messages_transcription_completed(self):
        """Test handling WebSocket message for transcription completion."""
        mock_logger = Mock()
        
        # Create a proper async iterator that yields the completion message
        # and then ends so the method can reach the completion point
        async def async_iter():
            yield '{"type": "conversation.item.input_audio_transcription.completed", "transcript": "Hello world"}'
            # End the iterator so the method can complete and return True
        
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__ = lambda self: async_iter()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        # The method returns early (implicitly None) when handling completion message
        assert result is None
        mock_logger.debug.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_websocket_messages_error(self):
        """Test handling WebSocket error message."""
        mock_logger = Mock()
        
        # Create a proper async iterator
        async def async_iter():
            yield '{"type": "error", "error": {"type": "test_error", "code": "123", "message": "Test error"}}'
        
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__ = lambda self: async_iter()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_websocket_messages_invalid_json(self):
        """Test handling invalid JSON in WebSocket message."""
        mock_logger = Mock()
        
        # Create a proper async iterator
        async def async_iter():
            yield 'invalid json message'
        
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__ = lambda self: async_iter()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_websocket_messages_connection_closed(self):
        """Test handling WebSocket connection closure."""
        mock_logger = Mock()
        
        # Create an async iterator that raises an exception on first iteration
        class ExceptionAsyncIterator:
            def __init__(self):
                self.called = False
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if not self.called:
                    self.called = True
                    raise Exception("Connection closed")
                raise StopAsyncIteration
        
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__ = lambda self: ExceptionAsyncIterator()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is False
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_close_websocket(self):
        """Test closing WebSocket connection."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        await handler.close()
        
        mock_websocket.close.assert_called_once()
    
    def test_get_session_id(self):
        """Test getting session ID."""
        mock_logger = Mock()
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger)
        handler.session_id = "test_session_id"
        
        result = handler.get_session_id()
        
        assert result == "test_session_id" 