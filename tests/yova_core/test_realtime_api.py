"""
Tests for the RealtimeApi class.

This test suite includes basic sound mocking to ensure all tests run silently:
- Mocks pydub.playback functions to prevent actual audio playback
- Mocks simpleaudio.PlayObject to prevent audio device access

While RealtimeApi doesn't directly play sound, it's used by Transcriber which does,
so we include basic sound mocking for consistency.
"""

import pytest
import asyncio
import json
import base64
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from websockets.exceptions import ConnectionClosed

from yova_core.speech2text.realtime_api import RealtimeApi


# Basic sound mocking to ensure tests are completely silent
@pytest.fixture(autouse=True)
def mock_sound_playing():
    """Mock sound playing functions to keep tests silent."""
    with patch('pydub.playback._play_with_simpleaudio') as mock_pydub_play:
        with patch('simpleaudio.PlayObject') as mock_play_object:
            # Mock sound playing functions to return safe mock objects
            mock_playback = Mock()
            mock_playback.wait_done = Mock()
            mock_pydub_play.return_value = mock_playback
            mock_play_object.return_value = mock_playback
            yield mock_pydub_play


class TestRealtimeApi:
    """Test cases for the RealtimeApi class."""

    def _create_realtime_api(self, api_key="test_api_key", logger=None, 
                            openai_client=None, websocket_connector=None):
        """Helper method to create a RealtimeApi instance for testing."""
        if logger is None:
            logger = Mock()
        
        return RealtimeApi(
            api_key=api_key,
            logger=logger,
            openai_client=openai_client,
            websocket_connector=websocket_connector
        )

    def test_init_default_values(self):
        """Test RealtimeApi initialization with default values."""
        api = self._create_realtime_api()
        
        assert api.api_key == "test_api_key"
        assert api.model == "gpt-4o-transcribe"
        assert api.language == "en"
        assert api.noise_reduction == "near_field"
        assert api.websocket is None
        assert api.session_id is None
        assert api.logger is not None

    def test_init_custom_values(self):
        """Test RealtimeApi initialization with custom values."""
        mock_openai_client = Mock()
        mock_websocket_connector = Mock()
        mock_logger = Mock()
        
        api = RealtimeApi(
            api_key="custom_key",
            logger=mock_logger,
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector,
            model="custom-model",
            language="es",
            noise_reduction="far_field"
        )
        
        assert api.api_key == "custom_key"
        assert api.model == "custom-model"
        assert api.language == "es"
        assert api.noise_reduction == "far_field"
        assert api._openai_client == mock_openai_client
        assert api._websocket_connector == mock_websocket_connector

    def test_is_connected_false(self):
        """Test is_connected property when not connected."""
        api = self._create_realtime_api()
        assert api.is_connected is False

    def test_is_connected_true(self):
        """Test is_connected property when connected."""
        api = self._create_realtime_api()
        api.websocket = Mock()
        api.websocket.closed = False
        api.session_id = "test_session_123"
        
        assert api.is_connected is True

    def test_is_connected_websocket_closed(self):
        """Test is_connected property when WebSocket is closed."""
        api = self._create_realtime_api()
        api.websocket = Mock()
        api.websocket.closed = True
        api.session_id = "test_session_123"
        
        assert api.is_connected is False

    def test_is_connected_no_session(self):
        """Test is_connected property when no session exists."""
        api = self._create_realtime_api()
        api.websocket = Mock()
        api.websocket.closed = False
        api.session_id = None
        
        assert api.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to OpenAI Realtime API."""
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.client_secret = "test_client_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.return_value = mock_response
        
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        
        # Mock the WebSocket connection
        mock_websocket_connector = AsyncMock()
        mock_websocket_connector.return_value = mock_websocket
        
        # Mock WebSocket messages
        messages = [
            json.dumps({
                "type": "transcription_session.created",
                "session": {"id": "test_session_123"}
            })
        ]
        mock_websocket.__aiter__ = lambda self: AsyncIterator(messages)
        
        api = self._create_realtime_api(
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector
        )
        
        result = await api.connect()
        
        assert result is True
        assert api.session_id == "test_session_123"
        assert api.websocket == mock_websocket
        mock_openai_client.beta.realtime.transcription_sessions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_transcription_session_failure(self):
        """Test connection failure when transcription session creation fails."""
        mock_openai_client = Mock()
        mock_openai_client.beta.realtime.transcription_sessions.create.side_effect = Exception("API Error")
        
        api = self._create_realtime_api(openai_client=mock_openai_client)
        
        result = await api.connect()
        
        assert result is False
        assert api.session_id is None
        assert api.websocket is None

    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self):
        """Test connection failure when WebSocket connection fails."""
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.client_secret = "test_client_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.return_value = mock_response
        
        mock_websocket_connector = AsyncMock()
        mock_websocket_connector.side_effect = Exception("WebSocket Error")
        
        api = self._create_realtime_api(
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector
        )
        
        result = await api.connect()
        
        assert result is False
        assert api.session_id is None
        assert api.websocket is None

    @pytest.mark.asyncio
    async def test_connect_error_message(self):
        """Test connection handling when error message is received."""
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.client_secret = "test_client_secret"
        mock_openai_client.beta.realtime.transcription_sessions.create.return_value = mock_response
        
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        
        mock_websocket_connector = AsyncMock()
        mock_websocket_connector.return_value = mock_websocket
        
        # Mock WebSocket error message
        messages = [
            json.dumps({
                "type": "error",
                "error": {
                    "type": "api_error",
                    "code": "invalid_request",
                    "message": "Invalid API key"
                }
            })
        ]
        mock_websocket.__aiter__ = lambda self: AsyncIterator(messages)
        
        api = self._create_realtime_api(
            openai_client=mock_openai_client,
            websocket_connector=mock_websocket_connector
        )
        
        result = await api.connect()
        
        assert result is False
        assert api.session_id is None

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection from OpenAI Realtime API."""
        api = self._create_realtime_api()
        mock_websocket = AsyncMock()
        api.websocket = mock_websocket
        api.session_id = "test_session_123"
        
        await api.disconnect()
        
        assert api.websocket is None
        assert api.session_id is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_websocket(self):
        """Test disconnection when no WebSocket exists."""
        api = self._create_realtime_api()
        api.websocket = None
        api.session_id = "test_session_123"
        
        await api.disconnect()
        
        assert api.websocket is None
        assert api.session_id is None

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful message sending."""
        api = self._create_realtime_api()
        api.websocket = AsyncMock()
        api.websocket.closed = False
        api.session_id = "test_session_123"
        
        message = {"type": "test", "data": "test_data"}
        result = await api.send(message)
        
        assert result is True
        api.websocket.send.assert_called_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_send_not_connected(self):
        """Test message sending when not connected."""
        api = self._create_realtime_api()
        api.websocket = None
        api.session_id = None
        
        message = {"type": "test", "data": "test_data"}
        result = await api.send(message, exception_on_error=False)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_connection_closed(self):
        """Test message sending when connection is closed."""
        api = self._create_realtime_api()
        api.websocket = AsyncMock()
        api.websocket.closed = False
        api.session_id = "test_session_123"
        api.websocket.send.side_effect = Exception("Connection closed")
        
        message = {"type": "test", "data": "test_data"}
        result = await api.send(message, exception_on_error=False)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_general_exception(self):
        """Test message sending when general exception occurs."""
        api = self._create_realtime_api()
        api.websocket = AsyncMock()
        api.websocket.closed = False
        api.session_id = "test_session_123"
        api.websocket.send.side_effect = Exception("General error")
        
        message = {"type": "test", "data": "test_data"}
        result = await api.send(message, exception_on_error=False)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_message_success(self):
        """Test successful message retrieval."""
        api = self._create_realtime_api()
        api.websocket = AsyncMock()
        api.websocket.closed = False
        api.session_id = "test_session_123"
        api.websocket.recv.return_value = '{"type": "test"}'
        
        result = await api.get_message()
        
        assert result == '{"type": "test"}'
        api.websocket.recv.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_not_connected(self):
        """Test message retrieval when not connected."""
        api = self._create_realtime_api()
        api.websocket = None
        api.session_id = None
        
        result = await api.get_message()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_send_audio_chunk(self):
        """Test sending audio chunk."""
        api = self._create_realtime_api()
        api.send = AsyncMock(return_value=True)
        
        audio_chunk = b"test_audio_data"
        result = await api.send_audio_chunk(audio_chunk)
        
        assert result is True
        expected_message = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_chunk).decode('utf-8')
        }
        api.send.assert_called_once_with(expected_message, 'audio_buffer.append', True)

    @pytest.mark.asyncio
    async def test_clear_audio_buffer(self):
        """Test clearing audio buffer."""
        api = self._create_realtime_api()
        api.send = AsyncMock(return_value=True)
        
        result = await api.clear_audio_buffer()
        
        assert result is True
        expected_message = {"type": "input_audio_buffer.clear"}
        api.send.assert_called_once_with(expected_message, 'audio_buffer.clear', True)

    @pytest.mark.asyncio
    async def test_commit_audio_buffer_success(self):
        """Test successful audio buffer commit."""
        api = self._create_realtime_api()
        api.send = AsyncMock(return_value=True)
        api.get_message_queue_length = Mock(return_value=0)
        
        # Mock WebSocket messages for commit response
        mock_websocket = AsyncMock()
        messages = [
            json.dumps({
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "Hello world"
            })
        ]
        mock_websocket.__aiter__ = lambda self: AsyncIterator(messages)
        api.websocket = mock_websocket
        
        result = await api.commit_audio_buffer()
        
        assert result == "Hello world"
        expected_message = {"type": "input_audio_buffer.commit"}
        api.send.assert_called_once_with(expected_message, 'audio_buffer.commit', True)

    @pytest.mark.asyncio
    async def test_commit_audio_buffer_failure(self):
        """Test audio buffer commit failure."""
        api = self._create_realtime_api()
        api.send = AsyncMock(return_value=False)
        api.get_message_queue_length = Mock(return_value=0)
        
        result = await api.commit_audio_buffer()
        
        assert result == ''

    @pytest.mark.asyncio
    async def test_commit_audio_buffer_error_message(self):
        """Test audio buffer commit with error message."""
        api = self._create_realtime_api()
        api.send = AsyncMock(return_value=True)
        api.get_message_queue_length = Mock(return_value=0)
        
        # Mock WebSocket messages for error response
        mock_websocket = AsyncMock()
        messages = [
            json.dumps({
                "type": "error",
                "error": {
                    "type": "api_error",
                    "code": "invalid_request",
                    "message": "Invalid audio format"
                }
            })
        ]
        mock_websocket.__aiter__ = lambda self: AsyncIterator(messages)
        api.websocket = mock_websocket
        
        result = await api.commit_audio_buffer()
        
        assert result == ''

    @pytest.mark.asyncio
    async def test_query_error_success(self):
        """Test successful error query."""
        api = self._create_realtime_api()
        api.get_message_queue_length = Mock(return_value=1)
        api.get_message = AsyncMock(return_value=json.dumps({
            "type": "error",
            "error": {
                "type": "api_error",
                "code": "invalid_request",
                "message": "Test error message"
            }
        }))
        
        result = await api.query_error()
        
        assert result == "Test error message"

    @pytest.mark.asyncio
    async def test_query_error_no_error(self):
        """Test error query when no error exists."""
        api = self._create_realtime_api()
        api.get_message_queue_length = Mock(return_value=0)
        
        result = await api.query_error()
        
        assert result is None

    def test_get_message_queue_length_connected(self):
        """Test getting message queue length when connected."""
        api = self._create_realtime_api()
        mock_websocket = Mock()
        mock_websocket.messages = ["msg1", "msg2", "msg3"]
        mock_websocket.closed = False
        api.websocket = mock_websocket
        api.session_id = "test_session_123"
        
        result = api.get_message_queue_length()
        
        assert result == 3

    def test_get_message_queue_length_not_connected(self):
        """Test getting message queue length when not connected."""
        api = self._create_realtime_api()
        api.websocket = None
        api.session_id = None
        
        result = api.get_message_queue_length()
        
        assert result == 0

    def test_get_session_config(self):
        """Test session configuration generation."""
        api = self._create_realtime_api()
        
        config = api._get_session_config("test-model", "fr", "far_field")
        
        expected_config = {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "test-model",
                "prompt": "",
                "language": "fr"
            },
            "turn_detection": None,
            "input_audio_noise_reduction": {
                "type": "far_field"
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }
        
        assert config == expected_config

    def test_get_session_config_defaults(self):
        """Test session configuration with default values."""
        api = self._create_realtime_api()
        
        config = api._get_session_config()
        
        expected_config = {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-transcribe",
                "prompt": "",
                "language": "en"
            },
            "turn_detection": None,
            "input_audio_noise_reduction": {
                "type": "near_field"
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }
        
        assert config == expected_config

    @pytest.mark.asyncio
    async def test_connect_websocket_success(self):
        """Test successful WebSocket connection."""
        api = self._create_realtime_api()
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        
        mock_websocket_connector = AsyncMock()
        mock_websocket_connector.return_value = mock_websocket
        
        api._websocket_connector = mock_websocket_connector
        
        result = await api._connect_websocket("test_client_secret")
        
        assert result is True
        assert api.websocket == mock_websocket
        mock_websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self):
        """Test WebSocket connection failure."""
        api = self._create_realtime_api()
        mock_websocket_connector = AsyncMock()
        mock_websocket_connector.side_effect = Exception("Connection failed")
        
        api._websocket_connector = mock_websocket_connector
        
        result = await api._connect_websocket("test_client_secret")
        
        assert result is False
        assert api.websocket is None


class AsyncIterator:
    """Helper class to create async iterators for testing."""
    
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
