"""Integration tests for the DataPlayback class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from voice_command_station.text2speech.data_playback import DataPlayback


class TestDataPlaybackIntegration:
    """Integration test cases for the DataPlayback class."""

    @pytest.mark.asyncio
    async def test_complete_tts_workflow(self):
        """Test a complete text-to-speech workflow."""
        # Mock OpenAI client
        mock_client = Mock()
        
        # Mock the speech creation response
        mock_response = AsyncMock()
        mock_response.aread.return_value = b"fake_audio_data_for_testing"
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        
        # Mock logger
        mock_logger = Mock()
        
        # Test text
        text = "Hello, this is a test of the text-to-speech system."
        
        # Create DataPlayback instance with custom config
        config = {
            "model": "gpt-4o-mini-tts",
            "voice": "alloy",
            "speed": 1.2,
            "instructions": "Speak clearly and naturally",
            "format": "mp3"
        }
        
        playback = DataPlayback(mock_client, mock_logger, text, config)
        
        # Mock audio playback components
        with patch('voice_command_station.text2speech.data_playback.AudioSegment') as mock_audio_segment_class, \
             patch('voice_command_station.text2speech.data_playback.play_audio') as mock_play_audio, \
             patch('voice_command_station.text2speech.data_playback.asyncio.to_thread') as mock_to_thread:
            
            mock_audio_segment = Mock()
            mock_playback = Mock()
            mock_playback.wait_done = Mock()
            
            mock_audio_segment_class.from_file.return_value = mock_audio_segment
            mock_play_audio.return_value = mock_playback
            mock_to_thread.side_effect = lambda func, *args: func(*args)
            
            # Execute the complete workflow
            await playback.load()
            await playback.play()
            
            # Verify the API call was made correctly
            mock_client.audio.speech.create.assert_called_once_with(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text,
                speed=1.2,
                response_format="mp3",
                instructions="Speak clearly and naturally"
            )
            
            # Verify audio data was loaded
            assert playback.audio_data == b"fake_audio_data_for_testing"
            
            # Verify audio playback was initiated
            mock_audio_segment_class.from_file.assert_called_once()
            mock_play_audio.assert_called_once_with(mock_audio_segment)
            mock_playback.wait_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_playback_instances(self):
        """Test creating and using multiple DataPlayback instances."""
        mock_logger = Mock()
        
        # Create multiple instances with different configurations
        texts = [
            "First message",
            "Second message", 
            "Third message"
        ]
        
        configs = [
            {"voice": "alloy", "speed": 1.0},
            {"voice": "echo", "speed": 1.5},
            {"voice": "fable", "speed": 0.8}
        ]
        
        playbacks = []
        
        # Create separate mock clients for each instance
        for i, (text, config) in enumerate(zip(texts, configs)):
            mock_client = Mock()
            mock_response = AsyncMock()
            mock_response.aread.return_value = f"audio_data_{i}".encode()
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            
            playback = DataPlayback(mock_client, mock_logger, text, config)
            playbacks.append(playback)
        
        # Load all playbacks
        for playback in playbacks:
            await playback.load()
        
        # Verify each playback has the correct data
        for i, playback in enumerate(playbacks):
            assert playback.audio_data == f"audio_data_{i}".encode()
            assert playback.voice == configs[i]["voice"]
            assert playback.speed == configs[i]["speed"]

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """Test error handling and recovery in a realistic scenario."""
        mock_client = Mock()
        mock_logger = Mock()
        
        # First attempt fails
        mock_client.audio.speech.create = AsyncMock(side_effect=Exception("API Error"))
        
        playback = DataPlayback(mock_client, mock_logger, "Test message")
        
        # First attempt should fail
        with pytest.raises(Exception, match="API Error"):
            await playback.load()
        
        # Retry with successful response
        mock_response = AsyncMock()
        mock_response.aread.return_value = b"recovered_audio_data"
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        
        # Second attempt should succeed
        await playback.load()
        assert playback.audio_data == b"recovered_audio_data"

    @pytest.mark.asyncio
    async def test_different_audio_formats(self):
        """Test DataPlayback with different audio formats."""
        mock_client = Mock()
        mock_logger = Mock()
        
        formats = ["mp3", "wav", "aac"]
        
        for audio_format in formats:
            mock_response = AsyncMock()
            mock_response.aread.return_value = f"audio_data_{audio_format}".encode()
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            
            config = {"format": audio_format}
            playback = DataPlayback(mock_client, mock_logger, f"Test {audio_format}", config)
            
            await playback.load()
            assert playback.format == audio_format
            assert playback.audio_data == f"audio_data_{audio_format}".encode()

    @pytest.mark.asyncio
    async def test_concurrent_playback_operations(self):
        """Test concurrent operations with DataPlayback instances."""
        mock_client = Mock()
        mock_logger = Mock()
        
        async def create_and_load_playback(text, config):
            mock_response = AsyncMock()
            mock_response.aread.return_value = f"audio_data_{text}".encode()
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            
            playback = DataPlayback(mock_client, mock_logger, text, config)
            await playback.load()
            return playback
        
        # Create multiple playbacks concurrently
        tasks = [
            create_and_load_playback("Task 1", {"voice": "alloy"}),
            create_and_load_playback("Task 2", {"voice": "echo"}),
            create_and_load_playback("Task 3", {"voice": "fable"})
        ]
        
        playbacks = await asyncio.gather(*tasks)
        
        # Verify all playbacks were created successfully
        assert len(playbacks) == 3
        for i, playback in enumerate(playbacks):
            assert playback.audio_data == f"audio_data_Task {i+1}".encode()
            assert playback.text == f"Task {i+1}" 