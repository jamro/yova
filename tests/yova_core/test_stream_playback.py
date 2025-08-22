"""Tests for the StreamPlayback class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from yova_core.text2speech.stream_playback import StreamPlayback


class TestStreamPlayback:
    """Test cases for the StreamPlayback class."""

    def test_init_with_default_config(self):
        """Test StreamPlayback initialization with default configuration."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Hello, world!"
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        assert playback.client == mock_client
        assert playback.text == text
        assert playback.stream_context_manager is None
        assert playback.model == "gpt-4o-mini-tts"
        assert playback.voice == "nova"
        assert playback.speed == 1
        assert playback.instructions == ""
        assert playback.format == "pcm"
        assert playback.stream_audio_player is not None
        assert playback.is_stopped == False
        assert playback.playback_task is None

    def test_init_with_custom_config(self):
        """Test StreamPlayback initialization with custom configuration."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Test message"
        config = {
            "model": "gpt-4o-tts",
            "voice": "alloy",
            "speed": 1.5,
            "instructions": "Speak slowly and clearly",
            "format": "wav"
        }
        
        playback = StreamPlayback(mock_client, mock_logger, text, config)
        
        assert playback.model == "gpt-4o-tts"
        assert playback.voice == "alloy"
        assert playback.speed == 1.5
        assert playback.instructions == "Speak slowly and clearly"
        assert playback.format == "wav"

    @pytest.mark.asyncio
    async def test_load_success(self):
        """Test successful stream loading."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Test audio generation"
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        await playback.load()
        
        # Verify the API call
        mock_client.audio.speech.with_streaming_response.create.assert_called_once_with(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=text,
            speed=1,
            response_format="pcm",
            instructions=""
        )
        
        assert playback.stream_context_manager == mock_stream_context

    @pytest.mark.asyncio
    async def test_load_with_custom_config(self):
        """Test stream loading with custom configuration."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Custom config test"
        config = {
            "model": "gpt-4o-tts",
            "voice": "echo",
            "speed": 0.8,
            "instructions": "Whisper mode",
            "format": "wav"
        }
        
        mock_stream_context = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text, config)
        
        await playback.load()
        
        # Verify the API call with custom config
        mock_client.audio.speech.with_streaming_response.create.assert_called_once_with(
            model="gpt-4o-tts",
            voice="echo",
            input=text,
            speed=0.8,
            response_format="wav",
            instructions="Whisper mode"
        )

    @pytest.mark.asyncio
    async def test_load_api_error(self):
        """Test stream loading when API call fails."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Error test"
        
        # Mock API error
        mock_client.audio.speech.with_streaming_response.create = Mock(
            side_effect=Exception("API Error")
        )
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        with pytest.raises(Exception, match="API Error"):
            await playback.load()

    @pytest.mark.asyncio
    async def test_play_success(self):
        """Test successful audio playback."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Test playback"
        
        # Mock the streaming response and audio player
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        await playback.play()
        
        # Verify the context manager was used correctly
        mock_stream_context.__aenter__.assert_called_once()
        mock_stream_context.__aexit__.assert_called_once_with(None, None, None)
        
        # Verify the audio player was called
        mock_audio_player.play.assert_called_once_with(mock_audio)
        
        # Verify logging
        mock_logger.debug.assert_called_once_with(f"Playing stream for text: {text}")

    @pytest.mark.asyncio
    async def test_play_without_load(self):
        """Test playback without loading first."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Test without load"
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        # This should work even without load() being called first
        # as the stream_context_manager will be None and the context manager
        # methods will be called on None
        with pytest.raises(AttributeError):
            await playback.play()

    @pytest.mark.asyncio
    async def test_play_audio_player_error(self):
        """Test playback when audio player fails."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Audio player error test"
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player to raise an error
        mock_audio_player = AsyncMock()
        mock_audio_player.play = AsyncMock(side_effect=Exception("Audio player error"))
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        
        with pytest.raises(Exception, match="Audio player error"):
            await playback.play()
        
        # With the improved implementation using try/finally, __aexit__ should be called
        # even when an exception occurs during playback
        mock_stream_context.__aenter__.assert_called_once()
        mock_stream_context.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_play_context_manager_error(self):
        """Test playback when context manager fails."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Context manager error test"
        
        # Mock the streaming response to fail on enter
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(side_effect=Exception("Context enter error"))
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        
        with pytest.raises(Exception, match="Context enter error"):
            await playback.play()
        
        # When __aenter__ fails, __aexit__ is still called due to the try/finally block
        mock_stream_context.__aenter__.assert_called_once()
        mock_stream_context.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test the complete workflow from initialization to playback."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Complete workflow test"
        config = {
            "model": "gpt-4o-tts",
            "voice": "nova",
            "speed": 1.2,
            "instructions": "Test instructions",
            "format": "mp3"
        }
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        # Create playback instance
        playback = StreamPlayback(mock_client, mock_logger, text, config)
        
        # Verify initial state
        assert playback.stream_context_manager is None
        assert playback.model == "gpt-4o-tts"
        assert playback.voice == "nova"
        assert playback.speed == 1.2
        assert playback.instructions == "Test instructions"
        assert playback.format == "mp3"
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        # Load the stream
        await playback.load()
        
        # Verify stream was loaded
        assert playback.stream_context_manager == mock_stream_context
        mock_client.audio.speech.with_streaming_response.create.assert_called_once_with(
            model="gpt-4o-tts",
            voice="nova",
            input=text,
            speed=1.2,
            response_format="mp3",
            instructions="Test instructions"
        )
        
        # Play the audio
        await playback.play()
        
        # Verify playback was successful
        mock_stream_context.__aenter__.assert_called_once()
        mock_stream_context.__aexit__.assert_called_once_with(None, None, None)
        mock_audio_player.play.assert_called_once_with(mock_audio)
        mock_logger.debug.assert_called_once_with(f"Playing stream for text: {text}")

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Logger test"
        
        with patch('yova_core.text2speech.stream_playback.get_clean_logger') as mock_get_logger:
            mock_clean_logger = Mock()
            mock_get_logger.return_value = mock_clean_logger
            
            playback = StreamPlayback(mock_client, mock_logger, text)
            
            mock_get_logger.assert_called_once_with("stream_playback", mock_logger)
            assert playback.logger == mock_clean_logger

    @pytest.mark.asyncio
    async def test_play_logging(self):
        """Test that play method logs correctly."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Logging test"
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        await playback.play()
        
        # Verify the debug log was called with the correct message
        mock_logger.debug.assert_called_once_with(f"Playing stream for text: {text}")

    def test_inheritance(self):
        """Test that StreamPlayback inherits from Playback."""
        from yova_core.text2speech.playback import Playback
        
        mock_client = Mock()
        mock_logger = Mock()
        text = "Inheritance test"
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        assert isinstance(playback, Playback)

    @pytest.mark.asyncio
    async def test_stop_functionality(self):
        """Test that stop function works correctly."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Stop test"
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player
        mock_audio_player = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        
        # Start playback in a separate task
        playback_task = asyncio.create_task(playback.play())
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Stop the playback
        await playback.stop()
        
        # Wait for the playback task to complete (should be cancelled)
        try:
            await playback_task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify stop was called
        mock_logger.debug.assert_any_call("Stopping stream playback")
        
        # Verify the playback task was cancelled or completed
        assert playback_task.done()
        
        # Verify the stream context was closed
        mock_stream_context.__aexit__.assert_called()

    @pytest.mark.asyncio
    async def test_stop_with_audio_player_stop_method(self):
        """Test stop function when audio player has a stop method."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Audio player stop test"
        
        # Mock the streaming response
        mock_stream_context = AsyncMock()
        mock_audio = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_audio)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_client.audio.speech.with_streaming_response.create = Mock(return_value=mock_stream_context)
        
        playback = StreamPlayback(mock_client, mock_logger, text)
        
        # Mock the audio player with a stop method
        mock_audio_player = AsyncMock()
        mock_audio_player.stop = AsyncMock()
        playback.stream_audio_player = mock_audio_player
        
        await playback.load()
        
        # Start playback in a separate task
        playback_task = asyncio.create_task(playback.play())
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Stop the playback
        await playback.stop()
        
        # Wait for the playback task to complete (should be cancelled)
        try:
            await playback_task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify the audio player's stop method was called
        mock_audio_player.stop.assert_called_once() 