"""
Tests for the Transcriber class.

This test suite focuses on testing the public API and behavior of the Transcriber class
while mocking external dependencies to ensure tests run reliably.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import numpy as np

from yova_core.speech2text.transcriber import Transcriber
from yova_core.speech2text.audio_buffer import get_audio_amplitude, get_audio_len
from yova_core.speech2text.realtime_api import RealtimeApi


# Mock audio-related functions to keep tests silent
@pytest.fixture(autouse=True)
def mock_audio_functions():
    """Mock audio functions to prevent actual audio playback and device access during tests."""
    with patch('yova_core.speech2text.transcriber.play_audio') as mock_play_audio:
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            with patch('wave.open') as mock_wave:
                with patch('pydub.playback._play_with_simpleaudio') as mock_pydub_play:
                    with patch('pydub.AudioSegment.from_wav') as mock_audio_segment:
                        # Mock PyAudio to prevent audio device access
                        mock_pyaudio_instance = Mock()
                        mock_pyaudio_instance.open.return_value = Mock()
                        mock_pyaudio_instance.get_sample_size.return_value = 2
                        mock_pyaudio.return_value = mock_pyaudio_instance
                        
                        # Mock wave module to prevent file I/O
                        mock_wave_file = Mock()
                        mock_wave.return_value.__enter__.return_value = mock_wave_file
                        
                        # Mock pydub to prevent audio playback
                        mock_playback = Mock()
                        mock_playback.wait_done = Mock()
                        mock_pydub_play.return_value = mock_playback
                        mock_audio_segment.return_value = Mock()
                        
                        # Mock asyncio.to_thread to prevent threading operations
                        with patch('asyncio.to_thread') as mock_to_thread:
                            mock_to_thread.side_effect = [mock_playback, None]
                            
                            yield mock_play_audio


class TestAudioUtils:
    """Test cases for audio utility functions."""

    def test_get_audio_amplitude_valid_chunk(self):
        """Test audio amplitude calculation with valid audio chunk."""
        audio_chunk = np.array([1000, -2000, 3000, -4000], dtype=np.int16).tobytes()
        result = get_audio_amplitude(audio_chunk)
        # Expected: max amplitude / 32768.0 = 4000 / 32768.0 ≈ 0.122
        assert result == pytest.approx(0.122, abs=0.001)

    def test_get_audio_amplitude_edge_cases(self):
        """Test audio amplitude calculation with edge cases."""
        assert get_audio_amplitude(b"") is None
        assert get_audio_amplitude(None) is None
        assert get_audio_amplitude(np.array([0, 0, 0, 0], dtype=np.int16).tobytes()) == 0.0

    def test_get_audio_len_valid_chunk(self):
        """Test audio length calculation with valid audio chunk."""
        audio_chunk = np.array([1000, -2000, 3000, -4000], dtype=np.int16).tobytes()
        result = get_audio_len(audio_chunk, 16000, 1)
        # Expected: 4 samples / (16000 Hz * 1 channel) = 0.00025 seconds
        assert result == pytest.approx(0.00025, abs=0.00001)

    def test_get_audio_len_edge_cases(self):
        """Test audio length calculation with edge cases."""
        assert get_audio_len(b"", 16000, 1) == 0.0
        assert get_audio_len(None, 16000, 1) == 0.0
        assert get_audio_len(np.array([], dtype=np.int16).tobytes(), 16000, 1) == 0.0


class TestTranscriber:
    """Test cases for the Transcriber class."""


    def _create_transcriber(self, **kwargs):
        """Helper method to create a Transcriber instance for testing."""
        defaults = {
            'logger': Mock(),
            'realtime_api': Mock(spec=RealtimeApi),
            'pyaudio_instance': Mock(),
        }
        defaults.update(kwargs)
        return Transcriber(**defaults)

    def test_init_default_values(self):
        """Test Transcriber initialization with default values."""
        transcriber = self._create_transcriber()
        
        assert transcriber.logger is not None
        assert transcriber.realtime_api is not None
        assert transcriber.recording_stream is not None
        assert transcriber.audio_buffer is not None
        assert transcriber.prerecord_beep == "beep1.wav"
        assert transcriber.beep_volume_reduction == 18
        assert transcriber.is_recording is False
        assert transcriber.listening_task is None

    def test_init_custom_values(self):
        """Test Transcriber initialization with custom values."""
        transcriber = self._create_transcriber(
            prerecord_beep="custom_beep.wav",
            beep_volume_reduction=20,
            silence_amplitude_threshold=0.2,
            min_speech_length=1.0,
            audio_logs_path="/tmp/audio_logs"
        )
        
        assert transcriber.prerecord_beep == "custom_beep.wav"
        assert transcriber.beep_volume_reduction == 20
        assert transcriber.audio_buffer.silence_amplitude_threshold == 0.2
        assert transcriber.audio_buffer.min_speech_length == 1.0
        assert transcriber.audio_buffer.audio_logs_path == "/tmp/audio_logs"

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self):
        """Test initialization and cleanup."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        transcriber = self._create_transcriber(realtime_api=mock_realtime_api)
        
        await transcriber.initialize()
        mock_realtime_api.connect.assert_called_once()
        
        await transcriber.cleanup()
        mock_realtime_api.disconnect.assert_called_once()
        assert transcriber.is_recording is False
        assert transcriber.listening_task is None

    @pytest.mark.asyncio
    async def test_start_listening(self):
        """Test starting listening."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        transcriber = self._create_transcriber(realtime_api=mock_realtime_api)
        
        await transcriber.start_listening()
        
        assert transcriber.listening_task is not None
        assert transcriber.audio_buffer.recording_start_time is not None

    @pytest.mark.asyncio
    async def test_stop_listening_success(self):
        """Test successful stop listening."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        mock_realtime_api.commit_audio_buffer.return_value = "Hello world"
        
        transcriber = self._create_transcriber(realtime_api=mock_realtime_api)
        transcriber.is_recording = True
        
        # Set up audio buffer to have content
        transcriber.audio_buffer.buffer = [b"chunk1", b"chunk2"]
        transcriber.audio_buffer.buffer_length = 1.0
        transcriber.audio_buffer.is_buffer_empty = False
        
        # Mock the event emission
        with patch.object(transcriber, 'emit_event', new_callable=AsyncMock) as mock_emit:
            result = await transcriber.stop_listening()
            
            assert result == "Hello world"
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[0]
            assert call_args[0] == "transcription_completed"
            assert "id" in call_args[1]
            assert call_args[1]["transcript"] == "Hello world"

    @pytest.mark.asyncio
    async def test_stop_listening_empty_buffer(self):
        """Test stop listening with empty buffer."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        transcriber = self._create_transcriber(realtime_api=mock_realtime_api)
        transcriber.is_recording = True
        
        with patch.object(transcriber, 'emit_event', new_callable=AsyncMock) as mock_emit:
            result = await transcriber.stop_listening()
            
            assert result == ""
            mock_emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_listening_with_audio_logs(self):
        """Test stop listening with audio logging enabled."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        mock_realtime_api.commit_audio_buffer.return_value = "Hello world"
        
        transcriber = self._create_transcriber(audio_logs_path="/tmp/audio_logs")
        transcriber.is_recording = True
        transcriber.audio_buffer.buffer = [b"chunk1", b"chunk2"]
        transcriber.audio_buffer.buffer_length = 1.0
        transcriber.audio_buffer.is_buffer_empty = False
        
        with patch.object(transcriber.audio_buffer, 'save_to_file', new_callable=AsyncMock) as mock_save:
            with patch.object(transcriber, 'emit_event', new_callable=AsyncMock):
                await transcriber.stop_listening()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_listening_exception_handling(self):
        """Test stop listening with exception handling."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        mock_realtime_api.commit_audio_buffer.side_effect = Exception("API Error")
        
        transcriber = self._create_transcriber(realtime_api=mock_realtime_api)
        transcriber.is_recording = True
        
        with patch.object(transcriber, 'emit_event', new_callable=AsyncMock) as mock_emit:
            result = await transcriber.stop_listening()
            
            assert result == ""
            mock_emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_and_transcribe_success(self):
        """Test successful listening and transcription."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        mock_recording_stream = Mock()
        mock_recording_stream.read.return_value = np.array([1000, -2000], dtype=np.int16).tobytes()
        
        transcriber = self._create_transcriber(
            realtime_api=mock_realtime_api,
            recording_stream=mock_recording_stream
        )
        
        with patch.object(transcriber, 'emit_event', new_callable=AsyncMock) as mock_emit:
            task = asyncio.create_task(transcriber._listen_and_transcribe())
            await asyncio.sleep(0.1)
            transcriber.is_recording = False
            await task
            
            mock_realtime_api.clear_audio_buffer.assert_called_once()
            mock_emit.assert_called_once_with("audio_recording_started", {"id": mock_emit.call_args[0][1]["id"]})

    @pytest.mark.asyncio
    async def test_listen_and_transcribe_with_beep_enabled(self):
        """Test that beep is configured when enabled."""
        transcriber = self._create_transcriber(prerecord_beep="beep1.wav")
        assert transcriber.prerecord_beep == "beep1.wav"
        assert transcriber.beep_volume_reduction == 18

    @pytest.mark.asyncio
    async def test_listen_and_transcribe_no_beep(self):
        """Test that no beep is configured when disabled."""
        transcriber = self._create_transcriber(prerecord_beep=None)
        assert transcriber.prerecord_beep is None

    @pytest.mark.asyncio
    async def test_listen_and_transcribe_error_handling(self):
        """Test listening with error handling."""
        mock_realtime_api = AsyncMock(spec=RealtimeApi)
        mock_realtime_api.query_error.return_value = "API Error"
        
        mock_recording_stream = Mock()
        mock_recording_stream.read.return_value = np.array([1000, -2000], dtype=np.int16).tobytes()
        
        transcriber = self._create_transcriber(
            realtime_api=mock_realtime_api,
            recording_stream=mock_recording_stream
        )
        
        with patch.object(transcriber, 'emit_event', new_callable=AsyncMock):
            task = asyncio.create_task(transcriber._listen_and_transcribe())
            await asyncio.sleep(0.1)
            transcriber.is_recording = False
            await task
            
            mock_realtime_api.query_error.assert_called()

    def test_recording_stream_properties(self):
        """Test recording stream properties."""
        transcriber = self._create_transcriber()
        
        assert transcriber.recording_stream is not None
        assert transcriber.recording_stream.channels == 1
        assert transcriber.recording_stream.rate == 16000
        assert transcriber.recording_stream.chunk == 512

    def test_audio_buffer_properties(self):
        """Test audio buffer properties."""
        transcriber = self._create_transcriber(
            silence_amplitude_threshold=0.2,
            min_speech_length=1.0
        )
        
        assert transcriber.audio_buffer.silence_amplitude_threshold == 0.2
        assert transcriber.audio_buffer.min_speech_length == 1.0

    @pytest.mark.asyncio
    async def test_play_audio_mocking(self, mock_audio_functions):
        """Test that play_audio function is properly mocked."""
        # Verify the mock is available
        assert mock_audio_functions is not None
        
        # Test that calling play_audio returns a mock object
        result = await mock_audio_functions("test.wav", 0)
        assert result is not None
        
        # Verify the mock was called
        mock_audio_functions.assert_called_once_with("test.wav", 0)
