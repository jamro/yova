"""Tests for the AudioRecorder class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from voice_command_station.speech2text.audio_recorder import AudioRecorder

# Mock pyaudio for testing
try:
    import pyaudio
except ImportError:
    # Create a mock pyaudio module for testing
    class MockPyAudio:
        paInt16 = 1
    pyaudio = MockPyAudio()


class TestAudioRecorder:
    """Test cases for the AudioRecorder class."""

    def test_init_with_default_dependencies(self):
        """Test AudioRecorder initialization with default dependencies."""
        mock_logger = Mock()
        
        with patch('voice_command_station.speech2text.audio_recorder.pyaudio.PyAudio') as mock_pyaudio:
            mock_pyaudio_instance = Mock()
            mock_pyaudio.return_value = mock_pyaudio_instance
            
            recorder = AudioRecorder(mock_logger)
            
            assert recorder.logger == mock_logger
            assert recorder.is_recording is False
            assert recorder.stream is None
            assert recorder._pyaudio_instance == mock_pyaudio_instance
            assert recorder._stream_factory == recorder._create_default_stream

    def test_init_with_injected_dependencies(self):
        """Test AudioRecorder initialization with injected dependencies."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream_factory = Mock()
        
        recorder = AudioRecorder(
            logger=mock_logger,
            pyaudio_instance=mock_pyaudio_instance,
            stream_factory=mock_stream_factory
        )
        
        assert recorder.logger == mock_logger
        assert recorder._pyaudio_instance == mock_pyaudio_instance
        assert recorder._stream_factory == mock_stream_factory

    def test_create_default_stream(self):
        """Test the default stream factory method."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio_instance.open.return_value = mock_stream
        
        recorder = AudioRecorder(mock_logger, pyaudio_instance=mock_pyaudio_instance)
        
        result = recorder._create_default_stream(mock_pyaudio_instance)
        
        mock_pyaudio_instance.open.assert_called_once_with(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=512
        )
        assert result == mock_stream

    def test_create_stream_uses_factory(self):
        """Test that _create_stream uses the configured factory."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream_factory = Mock()
        mock_stream = Mock()
        mock_stream_factory.return_value = mock_stream
        
        recorder = AudioRecorder(
            logger=mock_logger,
            pyaudio_instance=mock_pyaudio_instance,
            stream_factory=mock_stream_factory
        )
        
        result = recorder._create_stream()
        
        mock_stream_factory.assert_called_once_with(mock_pyaudio_instance)
        assert result == mock_stream

    def test_add_event_listener(self):
        """Test adding event listeners."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        listener = AsyncMock()
        
        recorder.add_event_listener("test_event", listener)
        
        assert recorder.event_emitter.has_listeners("test_event")
        assert recorder.event_emitter.get_listener_count("test_event") == 1

    def test_remove_event_listener(self):
        """Test removing event listeners."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        listener = AsyncMock()
        
        recorder.add_event_listener("test_event", listener)
        recorder.remove_event_listener("test_event", listener)
        
        assert not recorder.event_emitter.has_listeners("test_event")

    def test_clear_event_listeners(self):
        """Test clearing event listeners."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        recorder.add_event_listener("event1", listener1)
        recorder.add_event_listener("event2", listener2)
        recorder.clear_event_listeners("event1")
        
        assert not recorder.event_emitter.has_listeners("event1")
        assert recorder.event_emitter.has_listeners("event2")

    def test_start_recording(self):
        """Test starting recording."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        
        recorder.start_recording()
        
        assert recorder.is_recording is True

    def test_stop_recording(self):
        """Test stopping recording."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        recorder.is_recording = True
        
        recorder.stop_recording()
        
        assert recorder.is_recording is False

    def test_cleanup_stream_with_stream(self):
        """Test stream cleanup when stream exists."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        mock_stream = Mock()
        recorder.stream = mock_stream
        
        recorder._cleanup_stream()
        
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        assert recorder.stream is None

    def test_cleanup_stream_without_stream(self):
        """Test stream cleanup when no stream exists."""
        mock_logger = Mock()
        recorder = AudioRecorder(mock_logger)
        recorder.stream = None
        
        # Should not raise an exception
        recorder._cleanup_stream()
        
        assert recorder.stream is None

    def test_cleanup(self):
        """Test full cleanup."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        recorder = AudioRecorder(mock_logger, pyaudio_instance=mock_pyaudio_instance)
        recorder.is_recording = True
        
        recorder.cleanup()
        
        assert recorder.is_recording is False
        mock_pyaudio_instance.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_and_stream_basic_flow(self):
        """Test basic recording and streaming flow."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_stream_factory = Mock(return_value=mock_stream)
        
        # Mock audio data
        mock_audio_data = b"fake_audio_data"
        mock_stream.read.return_value = mock_audio_data
        
        recorder = AudioRecorder(
            logger=mock_logger,
            pyaudio_instance=mock_pyaudio_instance,
            stream_factory=mock_stream_factory
        )
        
        # Add a listener to capture events
        captured_events = []
        async def test_listener(data):
            captured_events.append(data)
        
        recorder.add_event_listener("audio_chunk", test_listener)
        recorder.start_recording()
        
        # Run recording for a short time
        recording_task = asyncio.create_task(recorder.record_and_stream())
        await asyncio.sleep(0.1)  # Let it run briefly
        recorder.stop_recording()
        
        try:
            await asyncio.wait_for(recording_task, timeout=1.0)
        except asyncio.TimeoutError:
            recording_task.cancel()
            try:
                await recording_task
            except asyncio.CancelledError:
                pass
        
        # Verify stream was created and used
        mock_stream_factory.assert_called_once_with(mock_pyaudio_instance)
        assert mock_stream.read.called
        
        # Verify events were emitted
        assert len(captured_events) > 0
        for event in captured_events:
            assert "audio_data" in event
            assert "chunk_size" in event
            assert "timestamp" in event
            assert event["audio_data"] == mock_audio_data

    @pytest.mark.asyncio
    async def test_record_and_stream_stream_exception(self):
        """Test recording when stream.read raises an exception."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_stream_factory = Mock(return_value=mock_stream)
        
        # Mock stream to raise an exception
        mock_stream.read.side_effect = Exception("Stream error")
        
        recorder = AudioRecorder(
            logger=mock_logger,
            pyaudio_instance=mock_pyaudio_instance,
            stream_factory=mock_stream_factory
        )
        
        recorder.start_recording()
        
        # Run recording - should handle the exception gracefully
        recording_task = asyncio.create_task(recorder.record_and_stream())
        await asyncio.sleep(0.1)  # Let it run briefly
        recorder.stop_recording()
        
        try:
            await asyncio.wait_for(recording_task, timeout=1.0)
        except asyncio.TimeoutError:
            recording_task.cancel()
            try:
                await recording_task
            except asyncio.CancelledError:
                pass
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args_list[0]
        assert "Error during audio streaming" in str(error_call)

    @pytest.mark.asyncio
    async def test_record_and_stream_recording_exception(self):
        """Test recording when the main recording loop raises an exception."""
        mock_logger = Mock()
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_stream_factory = Mock(side_effect=Exception("Recording error"))
        
        recorder = AudioRecorder(
            logger=mock_logger,
            pyaudio_instance=mock_pyaudio_instance,
            stream_factory=mock_stream_factory
        )
        
        recorder.start_recording()
        
        # Run recording - should handle the exception gracefully
        recording_task = asyncio.create_task(recorder.record_and_stream())
        
        # Wait for the task to complete (it should fail quickly due to the exception)
        try:
            await asyncio.wait_for(recording_task, timeout=2.0)
        except Exception:
            # The exception is expected, so we just pass
            pass
        
        recorder.stop_recording()
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args_list[0]
        assert "Error during recording" in str(error_call)

    def test_backward_compatibility(self):
        """Test that the new constructor maintains backward compatibility."""
        mock_logger = Mock()
        
        with patch('voice_command_station.speech2text.audio_recorder.pyaudio.PyAudio') as mock_pyaudio:
            mock_pyaudio_instance = Mock()
            mock_pyaudio.return_value = mock_pyaudio_instance
            
            # Test old constructor signature still works
            recorder = AudioRecorder(mock_logger)
            
            assert recorder.logger == mock_logger
            assert recorder._pyaudio_instance == mock_pyaudio_instance
            assert recorder._stream_factory == recorder._create_default_stream


if __name__ == "__main__":
    pytest.main([__file__]) 