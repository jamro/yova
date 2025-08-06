#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from voice_command_station.speech2text.realtime_transcriber import RealtimeTranscriber
from voice_command_station.speech2text.transcription_provider import TranscriptionProvider
from voice_command_station.speech2text.audio_recorder import AudioRecorder


class MockTranscriptionProvider(TranscriptionProvider):
    """Mock implementation of TranscriptionProvider for testing"""
    
    def __init__(self, ready_delay=0.1):
        self.event_emitter = Mock()
        self.initialized = False
        self.listening = False
        self.session_ready = False
        self.ready_delay = ready_delay
        self.initialize_called = False
        self.start_listening_called = False
        self.close_called = False
        self.audio_data_sent = []
        
    def add_event_listener(self, event_type: str, listener):
        self.event_emitter.add_event_listener(event_type, listener)
    
    def remove_event_listener(self, event_type: str, listener):
        self.event_emitter.remove_event_listener(event_type, listener)
    
    def clear_event_listeners(self, event_type: str = None):
        self.event_emitter.clear_event_listeners(event_type)
    
    async def initialize_session(self) -> bool:
        self.initialized = True
        self.initialize_called = True
        return True
    
    async def start_listening(self) -> bool:
        self.listening = True
        self.start_listening_called = True
        return True
    
    async def send_audio_data(self, audio_chunk: bytes) -> bool:
        self.audio_data_sent.append(audio_chunk)
        return True
    
    async def stop_listening(self):
        self.listening = False
    
    async def close(self):
        self.closed = True
        self.close_called = True
    
    def is_session_ready(self) -> bool:
        return self.session_ready
    
    async def set_session_ready(self, ready: bool):
        """Helper method to control session ready state for testing"""
        self.session_ready = ready
        if ready:
            await asyncio.sleep(self.ready_delay)


class MockAudioRecorder:
    """Mock implementation of AudioRecorder for testing"""
    
    def __init__(self):
        self.event_emitter = Mock()
        self.is_recording = False
        self.cleanup_called = False
        
    def add_event_listener(self, event_type: str, listener):
        self.event_emitter.add_event_listener(event_type, listener)
    
    def remove_event_listener(self, event_type: str, listener):
        self.event_emitter.remove_event_listener(event_type, listener)
    
    def clear_event_listeners(self, event_type: str = None):
        self.event_emitter.clear_event_listeners(event_type)
    
    def cleanup(self):
        self.cleanup_called = True


class TestRealtimeTranscriber:
    """Test cases for the RealtimeTranscriber class."""

    def test_init_with_default_parameters(self):
        """Test RealtimeTranscriber initialization with default parameters."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        assert transcriber.transcription_provider == mock_provider
        assert transcriber.audio_recorder == mock_recorder
        assert transcriber.logger == mock_logger
        assert transcriber.max_wait_time == 10
        assert transcriber.wait_interval == 0.1
        assert transcriber.is_initialized is False
        assert transcriber.is_listening is False
        assert transcriber.is_session_ready is False
        assert transcriber.is_active is False

    def test_init_with_custom_parameters(self):
        """Test RealtimeTranscriber initialization with custom parameters."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(
            mock_provider, 
            mock_recorder, 
            mock_logger,
            max_wait_time=5,
            wait_interval=0.05
        )
        
        assert transcriber.max_wait_time == 5
        assert transcriber.wait_interval == 0.05

    def test_init_with_on_completed_callback(self):
        """Test RealtimeTranscriber initialization with onCompleted callback."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        callback_called = False
        callback_data = None
        
        def on_completed(transcript):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = transcript
        
        transcriber = RealtimeTranscriber(
            mock_provider, 
            mock_recorder, 
            mock_logger,
            onCompleted=on_completed
        )
        
        # Verify event listener was added
        assert transcriber.event_emitter.has_listeners("transcription_completed")

    def test_setup_event_handlers(self):
        """Test that event handlers are properly set up."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Verify event listeners were added to both provider and recorder
        assert mock_provider.event_emitter.add_event_listener.called
        assert mock_recorder.event_emitter.add_event_listener.called

    def test_property_is_initialized(self):
        """Test the is_initialized property."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        assert transcriber.is_initialized is False
        
        transcriber._is_initialized = True
        assert transcriber.is_initialized is True

    def test_property_is_listening(self):
        """Test the is_listening property."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        assert transcriber.is_listening is False
        
        transcriber._is_listening = True
        assert transcriber.is_listening is True

    def test_property_is_session_ready(self):
        """Test the is_session_ready property."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        assert transcriber.is_session_ready is False
        
        transcriber._is_session_ready = True
        assert transcriber.is_session_ready is True

    def test_property_is_active(self):
        """Test the is_active property."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Initially all states are False
        assert transcriber.is_active is False
        
        # Set individual states
        transcriber._is_initialized = True
        assert transcriber.is_active is False
        
        transcriber._is_listening = True
        assert transcriber.is_active is False
        
        transcriber._is_session_ready = True
        assert transcriber.is_active is True

    def test_add_event_listener(self):
        """Test adding event listeners."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        listener = AsyncMock()
        
        transcriber.add_event_listener("test_event", listener)
        
        assert transcriber.event_emitter.has_listeners("test_event")

    def test_remove_event_listener(self):
        """Test removing event listeners."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        listener = AsyncMock()
        
        transcriber.add_event_listener("test_event", listener)
        transcriber.remove_event_listener("test_event", listener)
        
        assert not transcriber.event_emitter.has_listeners("test_event")

    def test_clear_event_listeners(self):
        """Test clearing event listeners."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        
        transcriber.add_event_listener("event1", listener1)
        transcriber.add_event_listener("event2", listener2)
        transcriber.clear_event_listeners("event1")
        
        assert not transcriber.event_emitter.has_listeners("event1")
        assert transcriber.event_emitter.has_listeners("event2")

    @pytest.mark.asyncio
    async def test_wait_for_session_ready_success(self):
        """Test waiting for session ready when it becomes ready within timeout."""
        mock_provider = MockTranscriptionProvider(ready_delay=0.05)
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger, max_wait_time=1, wait_interval=0.01)
        
        # Start a task to set session ready after a short delay
        async def set_ready():
            await asyncio.sleep(0.1)
            await mock_provider.set_session_ready(True)
        
        asyncio.create_task(set_ready())
        
        # Wait for session ready
        result = await transcriber._wait_for_session_ready()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_session_ready_timeout(self):
        """Test waiting for session ready when it times out."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger, max_wait_time=0.1, wait_interval=0.05)
        
        # Don't set session ready, should timeout
        result = await transcriber._wait_for_session_ready()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_start_realtime_transcription_success(self):
        """Test successful start of real-time transcription."""
        mock_provider = MockTranscriptionProvider(ready_delay=0.05)
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger, max_wait_time=1, wait_interval=0.01)
        
        # Start a task to set session ready after initialization
        async def set_ready():
            await asyncio.sleep(0.1)
            await mock_provider.set_session_ready(True)
        
        asyncio.create_task(set_ready())
        
        # Start transcription
        await transcriber.start_realtime_transcription()
        
        # Verify all states are set correctly
        assert transcriber.is_initialized is True
        assert transcriber.is_listening is True
        assert transcriber.is_session_ready is True
        assert transcriber.is_active is True
        
        # Verify provider methods were called
        assert mock_provider.initialize_called
        assert mock_provider.start_listening_called

    @pytest.mark.asyncio
    async def test_start_realtime_transcription_initialization_failure(self):
        """Test start_realtime_transcription when initialization fails."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        # Make initialization fail
        mock_provider.initialize_session = AsyncMock(return_value=False)
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Should raise an exception
        with pytest.raises(Exception, match="Failed to initialize transcription session"):
            await transcriber.start_realtime_transcription()
        
        # Verify states are reset
        assert transcriber.is_initialized is False
        assert transcriber.is_listening is False
        assert transcriber.is_session_ready is False

    @pytest.mark.asyncio
    async def test_start_realtime_transcription_listening_failure(self):
        """Test start_realtime_transcription when start_listening fails."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        # Make start_listening fail
        mock_provider.start_listening = AsyncMock(return_value=False)
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Should raise an exception
        with pytest.raises(Exception, match="Failed to start listening for transcription events"):
            await transcriber.start_realtime_transcription()
        
        # Verify states are reset
        assert transcriber.is_initialized is False
        assert transcriber.is_listening is False
        assert transcriber.is_session_ready is False

    @pytest.mark.asyncio
    async def test_start_realtime_transcription_session_not_ready(self):
        """Test start_realtime_transcription when session doesn't become ready."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger, max_wait_time=0.1, wait_interval=0.05)
        
        # Should raise an exception
        with pytest.raises(Exception, match="Session not ready within timeout period"):
            await transcriber.start_realtime_transcription()
        
        # Verify states are reset
        assert transcriber.is_initialized is False
        assert transcriber.is_listening is False
        assert transcriber.is_session_ready is False

    @pytest.mark.asyncio
    async def test_on_audio_chunk_success(self):
        """Test handling of audio chunk events."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        audio_data = b"test_audio_data"
        data = {"audio_data": audio_data}
        
        await transcriber._on_audio_chunk(data)
        
        # Verify audio data was sent to provider
        assert len(mock_provider.audio_data_sent) == 1
        assert mock_provider.audio_data_sent[0] == audio_data

    @pytest.mark.asyncio
    async def test_on_audio_chunk_failure(self):
        """Test handling of audio chunk events when sending fails."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Make send_audio_data fail
        mock_provider.send_audio_data = AsyncMock(return_value=False)
        
        audio_data = b"test_audio_data"
        data = {"audio_data": audio_data}
        
        await transcriber._on_audio_chunk(data)
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args_list[0]
        assert "Failed to send audio data" in str(warning_call)

    @pytest.mark.asyncio
    async def test_on_audio_chunk_no_audio_data(self):
        """Test handling of audio chunk events with no audio data."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        data = {"other_field": "value"}
        
        await transcriber._on_audio_chunk(data)
        
        # Verify no audio data was sent
        assert len(mock_provider.audio_data_sent) == 0

    @pytest.mark.asyncio
    async def test_on_transcription_completed(self):
        """Test handling of transcription completed events."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Add a listener to capture the event
        captured_event = None
        async def test_listener(data):
            nonlocal captured_event
            captured_event = data
        
        transcriber.add_event_listener("transcription_completed", test_listener)
        
        transcript_data = "Hello, world!"
        await transcriber._on_transcription_completed(transcript_data)
        
        # Verify event was emitted with correct data
        assert captured_event is not None
        assert captured_event["transcript"] == transcript_data
        assert "timestamp" in captured_event

    @pytest.mark.asyncio
    async def test_on_transcription_error(self):
        """Test handling of transcription error events."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Add a listener to capture the event
        captured_event = None
        async def test_listener(data):
            nonlocal captured_event
            captured_event = data
        
        transcriber.add_event_listener("error", test_listener)
        
        error_data = {"error": "Test error message"}
        await transcriber._on_transcription_error(error_data)
        
        # Verify event was emitted with correct data
        assert captured_event is not None
        assert captured_event["error"] == "Test error message"
        assert "timestamp" in captured_event

    @pytest.mark.asyncio
    async def test_on_transcription_error_no_error_field(self):
        """Test handling of transcription error events with no error field."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Add a listener to capture the event
        captured_event = None
        async def test_listener(data):
            nonlocal captured_event
            captured_event = data
        
        transcriber.add_event_listener("error", test_listener)
        
        error_data = {"other_field": "value"}
        await transcriber._on_transcription_error(error_data)
        
        # Verify event was emitted with default error message
        assert captured_event is not None
        assert captured_event["error"] == "Unknown error"
        assert "timestamp" in captured_event

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Set some states to True
        transcriber._is_initialized = True
        transcriber._is_listening = True
        transcriber._is_session_ready = True
        
        transcriber.cleanup()
        
        # Verify cleanup was called on dependencies
        assert mock_recorder.cleanup_called
        
        # Give the async task a chance to run
        await asyncio.sleep(0.01)
        
        # Verify close was called (it's scheduled as a task)
        assert mock_provider.close_called
        
        # Verify states are reset
        assert transcriber.is_initialized is False
        assert transcriber.is_listening is False
        assert transcriber.is_session_ready is False

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test internal event emission."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        transcriber = RealtimeTranscriber(mock_provider, mock_recorder, mock_logger)
        
        # Add a listener to capture the event
        captured_event = None
        async def test_listener(data):
            nonlocal captured_event
            captured_event = data
        
        transcriber.add_event_listener("test_event", test_listener)
        
        test_data = {"key": "value"}
        await transcriber._emit_event("test_event", test_data)
        
        # Verify event was emitted
        assert captured_event == test_data

    @pytest.mark.asyncio
    async def test_integration_with_on_completed_callback(self):
        """Test integration with onCompleted callback."""
        mock_provider = MockTranscriptionProvider()
        mock_recorder = MockAudioRecorder()
        mock_logger = Mock()
        
        callback_called = False
        callback_transcript = None
        
        def on_completed(transcript):
            nonlocal callback_called, callback_transcript
            callback_called = True
            callback_transcript = transcript
        
        transcriber = RealtimeTranscriber(
            mock_provider, 
            mock_recorder, 
            mock_logger,
            onCompleted=on_completed
        )
        
        # Simulate transcription completion
        transcript_data = "Test transcript"
        await transcriber._on_transcription_completed(transcript_data)
        
        # Verify callback was called
        assert callback_called
        assert callback_transcript == transcript_data


if __name__ == "__main__":
    pytest.main([__file__]) 