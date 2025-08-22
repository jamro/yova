"""Tests for the DataPlayback class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch, mock_open
from io import BytesIO
# AudioSegment is mocked in tests, no need to import it
from yova_core.text2speech.data_playback import DataPlayback


class TestDataPlayback:
    """Test cases for the DataPlayback class."""

    def test_init_with_default_config(self):
        """Test DataPlayback initialization with default configuration."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Hello, world!"
        
        playback = DataPlayback(mock_client, mock_logger, text)
        
        assert playback.client == mock_client
        assert playback.text == text
        assert playback.audio_data is None
        assert playback.model == "gpt-4o-mini-tts"
        assert playback.voice == "coral"
        assert playback.speed == 1
        assert playback.instructions == ""
        assert playback.format == "mp3"

    def test_init_with_custom_config(self):
        """Test DataPlayback initialization with custom configuration."""
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
        
        playback = DataPlayback(mock_client, mock_logger, text, config)
        
        assert playback.model == "gpt-4o-tts"
        assert playback.voice == "alloy"
        assert playback.speed == 1.5
        assert playback.instructions == "Speak slowly and clearly"
        assert playback.format == "wav"

    @pytest.mark.asyncio
    async def test_load_success(self):
        """Test successful audio loading."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Test audio generation"
        
        # Mock the response
        mock_response = AsyncMock()
        mock_response.aread.return_value = b"fake_audio_data"
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        
        playback = DataPlayback(mock_client, mock_logger, text)
        
        await playback.load()
        
        # Verify the API call
        mock_client.audio.speech.create.assert_called_once_with(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=text,
            speed=1,
            response_format="mp3",
            instructions=""
        )
        
        # Verify the response was read
        mock_response.aread.assert_called_once()
        assert playback.audio_data == b"fake_audio_data"

    @pytest.mark.asyncio
    async def test_load_with_custom_config(self):
        """Test audio loading with custom configuration."""
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
        
        mock_response = AsyncMock()
        mock_response.aread.return_value = b"custom_audio_data"
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        
        playback = DataPlayback(mock_client, mock_logger, text, config)
        
        await playback.load()
        
        # Verify the API call with custom config
        mock_client.audio.speech.create.assert_called_once_with(
            model="gpt-4o-tts",
            voice="echo",
            input=text,
            speed=0.8,
            response_format="wav",
            instructions="Whisper mode"
        )
        
        assert playback.audio_data == b"custom_audio_data"

    @pytest.mark.asyncio
    async def test_load_api_error(self):
        """Test handling of API errors during loading."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Error test"
        
        # Mock API error
        mock_client.audio.speech.create = AsyncMock(side_effect=Exception("API Error"))
        
        playback = DataPlayback(mock_client, mock_logger, text)
        
        with pytest.raises(Exception, match="API Error"):
            await playback.load()

    @pytest.mark.asyncio
    async def test_play_success(self):
        """Test successful audio playback."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Playback test"
        
        # Mock audio data
        audio_data = b"fake_audio_data"
        
        # Mock AudioSegment and playback
        mock_audio_segment = Mock()
        mock_playback = Mock()
        mock_playback.wait_done = Mock()
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('yova_core.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('yova_core.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.return_value = mock_playback
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            playback = DataPlayback(mock_client, mock_logger, text)
            playback.audio_data = audio_data
            
            await playback.play()
            
            # Verify AudioSegment was created correctly
            mock_audio_segment_class.from_file.assert_called_once()
            call_args = mock_audio_segment_class.from_file.call_args
            assert isinstance(call_args[0][0], BytesIO)
            assert call_args[1]['format'] == 'mp3'
            
            # Verify play_audio was called
            mock_play_audio.assert_called_once_with(mock_audio_segment)
            
            # Verify wait_done was called
            mock_playback.wait_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_with_different_format(self):
        """Test audio playback with different audio format."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Format test"
        config = {"format": "wav"}
        
        audio_data = b"wav_audio_data"
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('yova_core.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('yova_core.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment = Mock()
            mock_playback = Mock()
            mock_playback.wait_done = Mock()
            
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.return_value = mock_playback
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            playback = DataPlayback(mock_client, mock_logger, text, config)
            playback.audio_data = audio_data
            
            await playback.play()
            
            # Verify format was passed correctly
            call_args = mock_audio_segment_class.from_file.call_args
            assert call_args[1]['format'] == 'wav'

    @pytest.mark.asyncio
    async def test_play_without_audio_data(self):
        """Test playback when no audio data is loaded."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "No data test"
        
        playback = DataPlayback(mock_client, mock_logger, text)
        # audio_data is None by default
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class:
            mock_audio_segment_class.from_file.side_effect = Exception("No audio data")
            
            with pytest.raises(Exception, match="No audio data"):
                await playback.play()

    @pytest.mark.asyncio
    async def test_play_audio_segment_error(self):
        """Test handling of AudioSegment creation errors."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "AudioSegment error test"
        audio_data = b"invalid_audio_data"
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class:
            mock_audio_segment_class.from_file.side_effect = Exception("Invalid audio format")
            
            playback = DataPlayback(mock_client, mock_logger, text)
            playback.audio_data = audio_data
            
            with pytest.raises(Exception, match="Invalid audio format"):
                await playback.play()

    @pytest.mark.asyncio
    async def test_play_playback_error(self):
        """Test handling of playback errors."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Playback error test"
        audio_data = b"audio_data"
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('yova_core.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('yova_core.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment = Mock()
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.side_effect = Exception("Playback failed")
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            playback = DataPlayback(mock_client, mock_logger, text)
            playback.audio_data = audio_data
            
            with pytest.raises(Exception, match="Playback failed"):
                await playback.play()

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test the complete workflow: load and play."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Complete workflow test"
        audio_data = b"workflow_audio_data"
        
        # Mock the response
        mock_response = AsyncMock()
        mock_response.aread.return_value = audio_data
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        
        # Mock audio playback
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('yova_core.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('yova_core.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment = Mock()
            mock_playback = Mock()
            mock_playback.wait_done = Mock()
            
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.return_value = mock_playback
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            playback = DataPlayback(mock_client, mock_logger, text)
            
            # Load the audio
            await playback.load()
            assert playback.audio_data == audio_data
            
            # Play the audio
            await playback.play()
            
            # Verify all the expected calls
            mock_client.audio.speech.create.assert_called_once()
            mock_audio_segment_class.from_file.assert_called_once()
            mock_play_audio.assert_called_once_with(mock_audio_segment)
            mock_playback.wait_done.assert_called_once()

    def test_logger_initialization(self):
        """Test that logger is properly initialized with clean logger."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Logger test"
        
        with patch('yova_core.text2speech.data_playback.get_clean_logger') as mock_get_clean_logger:
            mock_clean_logger = Mock()
            mock_get_clean_logger.return_value = mock_clean_logger
            
            playback = DataPlayback(mock_client, mock_logger, text)
            
            mock_get_clean_logger.assert_called_once_with("data_playback", mock_logger)
            assert playback.logger == mock_clean_logger

    @pytest.mark.asyncio
    async def test_play_logging(self):
        """Test that play method logs appropriately."""
        mock_client = Mock()
        mock_logger = Mock()
        text = "Logging test"
        audio_data = b"logging_audio_data"
        
        with patch('yova_core.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('yova_core.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('yova_core.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment = Mock()
            mock_playback = Mock()
            mock_playback.wait_done = Mock()
            
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.return_value = mock_playback
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            playback = DataPlayback(mock_client, mock_logger, text)
            playback.audio_data = audio_data
            
            await playback.play()
            
            # Verify debug logging
            playback.logger.debug.assert_called_once_with(f"Playing data for text: {text}") 