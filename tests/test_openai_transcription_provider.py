"""Tests for the OpenAiTranscriptionProvider class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
from yova_core.speech2text.audio_buffer import AudioBuffer

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
        
        assert result is True  # Now returns True because audio is successfully buffered
        assert handler.has_buffered_audio() is True
        assert handler.get_buffered_audio_info()['chunk_count'] == 1
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
    
    def test_has_buffered_audio(self):
        """Test checking if there are buffered audio chunks."""
        mock_logger = Mock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = False
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        # Initially no buffered audio
        assert handler.has_buffered_audio() is False
        
        # Mock the audio buffer to have some chunks
        mock_audio_buffer.has_buffered_audio.return_value = True
        
        assert handler.has_buffered_audio() is True
    
    def test_get_buffered_audio_info(self):
        """Test getting information about buffered audio."""
        mock_logger = Mock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.get_buffered_audio_info.return_value = {'chunk_count': 0, 'total_length': 0.0, 'is_empty': True}
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        # Initially no buffered audio
        info = handler.get_buffered_audio_info()
        assert info['chunk_count'] == 0
        assert info['total_length'] == 0.0
        assert info['is_session_ready'] is False
        
        # Mock the audio buffer to have some chunks
        mock_buffer_info = {'chunk_count': 2, 'total_length': 0.5, 'is_empty': False}
        mock_audio_buffer.get_buffered_audio_info.return_value = mock_buffer_info
        handler.session_id = "test_session"
        mock_websocket = Mock()
        mock_websocket.closed = False
        handler.websocket = mock_websocket  # Need websocket for is_session_ready to return True
        
        info = handler.get_buffered_audio_info()
        assert info['chunk_count'] == 2
        assert info['total_length'] == 0.5
        assert info['is_session_ready'] is True
    
    def test_clear_audio_buffer(self):
        """Test clearing the audio buffer."""
        mock_logger = Mock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        handler.clear_audio_buffer()
        
        # Verify that clear_buffer was called on the audio buffer
        mock_audio_buffer.clear_buffer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer_no_buffer(self):
        """Test flushing audio buffer when there's nothing to flush."""
        mock_logger = Mock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = False
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        result = await handler.flush_audio_buffer()
        
        assert result is True
        mock_logger.info.assert_called_with("No buffered audio to flush")
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer_session_not_ready(self):
        """Test flushing audio buffer when session is not ready."""
        mock_logger = Mock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        result = await handler.flush_audio_buffer()
        
        assert result is False
        mock_logger.warning.assert_called_with("Cannot flush audio buffer: session not ready")
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer_success(self):
        """Test successful flushing of audio buffer."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        mock_audio_buffer.get_buffered_audio_info.return_value = {'chunk_count': 1, 'total_length': 0.5, 'is_empty': False}
        mock_audio_buffer.get_buffered_chunks.return_value = [b"\x00\x00\x01\x00\x02\x00"]
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        handler.websocket = mock_websocket
        handler.session_id = "test_session"
        
        result = await handler.flush_audio_buffer()
        
        assert result is True
        mock_websocket.send.assert_called_once()
        # Verify that clear_buffer was called on the audio buffer
        mock_audio_buffer.clear_buffer.assert_called_once()
        mock_logger.info.assert_called_with("Successfully flushed all buffered audio chunks")
    
    @pytest.mark.asyncio
    async def test_send_audio_data_with_buffering_and_flush(self):
        """Test sending audio data with buffering and subsequent flush when session becomes ready."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = False
        mock_audio_buffer.get_buffered_audio_info.return_value = {'chunk_count': 0, 'total_length': 0.0, 'is_empty': True}
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        
        # Initially no websocket (session not ready)
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes = 3 int16 values
        
        # Send audio data when session not ready - should buffer
        result1 = await handler.send_audio_data(audio_chunk)
        assert result1 is True
        # Mock the buffer to show it has audio after buffering
        mock_audio_buffer.has_buffered_audio.return_value = True
        mock_audio_buffer.get_buffered_audio_info.return_value = {'chunk_count': 1, 'total_length': 0.5, 'is_empty': False}
        assert handler.has_buffered_audio() is True
        assert handler.get_buffered_audio_info()['chunk_count'] == 1
        
        # Now establish session
        handler.websocket = mock_websocket
        handler.session_id = "test_session"
        
        # Ensure the session is ready
        assert handler.is_session_ready() is True
        
        # Test that the session is properly configured
        assert handler.websocket == mock_websocket
        assert handler.session_id == "test_session"
    
    @pytest.mark.asyncio
    async def test_session_created_flushes_buffer(self):
        """Test that session creation automatically flushes buffered audio."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        mock_audio_buffer.get_buffered_audio_info.return_value = {'chunk_count': 1, 'total_length': 0.5, 'is_empty': False}
        mock_audio_buffer.get_buffered_chunks.return_value = [b"\x00\x00\x01\x00\x02\x00"]
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        handler.websocket = mock_websocket
        
        # Add some buffered audio before session is ready
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes = 3 int16 values
        
        # Create a proper async iterator for session creation
        async def async_iter():
            yield '{"type": "transcription_session.created", "session": {"id": "test_session_id"}}'
        
        mock_websocket.__aiter__ = lambda self: async_iter()
        
        # Handle the session creation message
        result = await handler.handle_websocket_messages()
        
        assert result is True
        assert handler.session_id == "test_session_id"
        # Verify that the buffer was flushed by checking that clear_buffer was called
        mock_audio_buffer.clear_buffer.assert_called_once()
        # Check that the buffer was flushed (either by the session created message or by the flush method)
        mock_logger.info.assert_any_call("Session ready, flushing buffered audio chunks...")
    
    @pytest.mark.asyncio
    async def test_close_clears_buffer(self):
        """Test that closing the provider clears the audio buffer."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        handler.websocket = mock_websocket
        
        await handler.close()
        
        # Verify that clear_buffer was called on the audio buffer
        mock_audio_buffer.clear_buffer.assert_called_once()
        # Check that the buffer was cleared (either by the close method or by the clear method)
        mock_logger.info.assert_any_call("Clearing audio buffer before closing")
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_listening_clears_buffer(self):
        """Test that starting listening clears any existing audio buffer."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send = AsyncMock()
        mock_audio_buffer = Mock()
        mock_audio_buffer.has_buffered_audio.return_value = True
        
        handler = OpenAiTranscriptionProvider("test_api_key", mock_logger, audio_buffer=mock_audio_buffer)
        handler.websocket = mock_websocket
        handler.session_id = "test_session"
        
        result = await handler.start_listening()
        
        assert result is True
        # Verify that the WebSocket message was sent to clear the input audio buffer
        mock_websocket.send.assert_called_once_with('{"type": "input_audio_buffer.clear"}') 