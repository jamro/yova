"""Tests for the WebSocketHandler class."""

import pytest
import json
import base64
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from voice_command_station.speech2text.websocket_handler import WebSocketHandler


class TestWebSocketHandler:
    """Test cases for the WebSocketHandler class."""

    def test_init_default_dependencies(self):
        """Test WebSocketHandler initialization with default dependencies."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        
        assert handler.api_key == "test_api_key"
        assert handler.logger == mock_logger
        assert handler.websocket_uri == "wss://api.openai.com/v1/realtime"
        assert handler.websocket is None
        assert handler.session_id is None
        assert handler._logged_invalid_request is False
        assert handler.event_emitter is not None

    def test_init_with_custom_dependencies(self):
        """Test WebSocketHandler initialization with injected dependencies."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_websocket_connector = Mock()
        
        handler = WebSocketHandler(
            "test_api_key", 
            mock_logger,
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector
        )
        
        assert handler._openai_client == mock_openai_client
        assert handler._websocket_connector == mock_websocket_connector

    def test_init_with_custom_websocket_uri(self):
        """Test WebSocketHandler initialization with custom WebSocket URI."""
        mock_logger = Mock()
        custom_uri = "wss://custom.example.com/v1/realtime"
        
        handler = WebSocketHandler("test_api_key", mock_logger, websocket_uri=custom_uri)
        
        assert handler.websocket_uri == custom_uri

    def test_add_event_listener(self):
        """Test adding event listeners."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        listener = AsyncMock()
        
        handler.add_event_listener("test_event", listener)
        
        assert handler.event_emitter.has_listeners("test_event")

    def test_remove_event_listener(self):
        """Test removing event listeners."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        listener = AsyncMock()
        
        handler.add_event_listener("test_event", listener)
        handler.remove_event_listener("test_event", listener)
        
        assert not handler.event_emitter.has_listeners("test_event")

    def test_clear_event_listeners(self):
        """Test clearing event listeners."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        listener = AsyncMock()
        
        handler.add_event_listener("test_event", listener)
        handler.clear_event_listeners("test_event")
        
        assert not handler.event_emitter.has_listeners("test_event")

    @pytest.mark.asyncio
    async def test_create_transcription_session_success(self):
        """Test successful transcription session creation."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.client_secret = "test_client_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.return_value = mock_response
        
        handler = WebSocketHandler("test_api_key", mock_logger, openai_client=mock_openai_client)
        
        result = await handler.create_transcription_session()
        
        assert result == "test_client_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_transcription_session_failure(self):
        """Test transcription session creation failure."""
        mock_logger = Mock()
        mock_openai_client = Mock()
        mock_openai_client.beta.realtime.transcription_sessions.create.side_effect = Exception("API Error")
        
        handler = WebSocketHandler("test_api_key", mock_logger, openai_client=mock_openai_client)
        
        result = await handler.create_transcription_session()
        
        assert result is None
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_websocket_success(self):
        """Test successful WebSocket connection."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket_connector = AsyncMock(return_value=mock_websocket)
        
        handler = WebSocketHandler("test_api_key", mock_logger, websocket_connector=mock_websocket_connector)
        
        result = await handler.connect_websocket("test_client_secret")
        
        assert result is True
        assert handler.websocket == mock_websocket
        mock_websocket_connector.assert_called_once()
        mock_websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self):
        """Test WebSocket connection failure."""
        mock_logger = Mock()
        mock_websocket_connector = AsyncMock(side_effect=Exception("Connection Error"))
        
        handler = WebSocketHandler("test_api_key", mock_logger, websocket_connector=mock_websocket_connector)
        
        result = await handler.connect_websocket("test_client_secret")
        
        assert result is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_data_success(self):
        """Test successful audio data sending."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = "test_session_id"
        
        audio_chunk = b"test_audio_data"
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is True
        mock_websocket.send.assert_called_once()
        
        # Verify the sent message structure
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message["type"] == "input_audio_buffer.append"
        assert "audio" in sent_message

    @pytest.mark.asyncio
    async def test_send_audio_data_no_session_id(self):
        """Test audio data sending when session ID is not available."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = None
        
        audio_chunk = b"test_audio_data"
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is False
        mock_websocket.send.assert_not_called()
        mock_logger.warning.assert_called_with("Cannot send audio data: WebSocket not connected or session not ready")

    @pytest.mark.asyncio
    async def test_send_audio_data_connection_closed(self):
        """Test audio data sending when WebSocket connection is closed."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = True
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = "test_session_id"
        
        audio_chunk = b"test_audio_data"
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is False
        mock_websocket.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_audio_data_websocket_exception(self):
        """Test audio data sending when WebSocket raises an exception."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.send.side_effect = Exception("Send Error")
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler.session_id = "test_session_id"
        
        audio_chunk = b"test_audio_data"
        result = await handler.send_audio_data(audio_chunk)
        
        assert result is False
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_no_websocket(self):
        """Test handling WebSocket messages when no WebSocket is connected."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = None
        
        result = await handler.handle_websocket_messages()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_session_created(self):
        """Test handling WebSocket messages for session creation."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        # Mock the async iterator for websocket messages
        session_message = {
            "type": "transcription_session.created",
            "session": {"id": "test_session_id"}
        }
        mock_websocket.__aiter__.return_value = [json.dumps(session_message)]
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        # Mock the emit_event method to avoid async issues in testing
        handler._emit_event = AsyncMock()
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        assert handler.session_id == "test_session_id"
        handler._emit_event.assert_called_once_with("transcription_session.created", session_message)

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_transcription_delta(self):
        """Test handling WebSocket messages for transcription delta."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        delta_message = {
            "type": "conversation.item.input_audio_transcription.delta",
            "delta": "Hello"
        }
        mock_websocket.__aiter__.return_value = [json.dumps(delta_message)]
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler._emit_event = AsyncMock()
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        handler._emit_event.assert_called_once_with("conversation.item.input_audio_transcription.delta", delta_message)

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_transcription_completed(self):
        """Test handling WebSocket messages for transcription completion."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        completed_message = {
            "type": "conversation.item.input_audio_transcription.completed",
            "transcript": "Hello world"
        }
        mock_websocket.__aiter__.return_value = [json.dumps(completed_message)]
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler._emit_event = AsyncMock()
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        handler._emit_event.assert_called_once_with("conversation.item.input_audio_transcription.completed", completed_message)

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_error(self):
        """Test handling WebSocket messages for error events."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        error_message = {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "code": "invalid_api_key",
                "message": "Invalid API key"
            }
        }
        mock_websocket.__aiter__.return_value = [json.dumps(error_message)]
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        handler._emit_event = AsyncMock()
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        handler._emit_event.assert_called_once_with("error", error_message)
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_json_decode_error(self):
        """Test handling WebSocket messages with JSON decode error."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        # Send invalid JSON
        mock_websocket.__aiter__.return_value = ["invalid json"]
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is True
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_websocket_messages_connection_closed(self):
        """Test handling WebSocket messages when connection is closed."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.side_effect = Exception("Connection closed")
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        result = await handler.handle_websocket_messages()
        
        assert result is False
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_close_websocket(self):
        """Test closing WebSocket connection."""
        mock_logger = Mock()
        mock_websocket = AsyncMock()
        
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = mock_websocket
        
        await handler.close()
        
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_websocket(self):
        """Test closing when no WebSocket is connected."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.websocket = None
        
        # Should not raise an exception
        await handler.close()

    def test_get_session_id(self):
        """Test getting session ID."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.session_id = "test_session_id"
        
        assert handler.get_session_id() == "test_session_id"

    def test_get_session_id_none(self):
        """Test getting session ID when it's None."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        handler.session_id = None
        
        assert handler.get_session_id() is None

    @pytest.mark.asyncio
    async def test_emit_event_integration(self):
        """Test event emission integration with EventEmitter."""
        mock_logger = Mock()
        handler = WebSocketHandler("test_api_key", mock_logger)
        
        # Add a test listener
        test_listener = AsyncMock()
        handler.add_event_listener("test_event", test_listener)
        
        # Emit an event
        test_data = {"key": "value"}
        await handler._emit_event("test_event", test_data)
        
        # Verify the listener was called
        test_listener.assert_called_once_with(test_data)


if __name__ == "__main__":
    pytest.main([__file__]) 