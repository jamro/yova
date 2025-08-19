#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from yova_core.speech2text.transcription_provider import TranscriptionProvider
from yova_core.speech2text.realtime_transcriber import RealtimeTranscriber
from yova_core.speech2text.audio_recorder import AudioRecorder


class MockTranscriptionProvider(TranscriptionProvider):
    """Mock implementation of TranscriptionProvider for testing"""
    
    def __init__(self):
        self.event_emitter = Mock()
        self.initialized = False
        self.listening = False
        self.closed = False
        self.initialize_called = False
        self.start_listening_called = False
        self.close_called = False
        
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
        return True
    
    async def stop_listening(self):
        self.listening = False
    
    async def close(self):
        self.closed = True
        self.close_called = True
    
    def is_session_ready(self) -> bool:
        return self.initialized and self.listening


class TestTranscriptionProviderAbstraction:
    """Test that RealtimeTranscriber properly uses TranscriptionProvider abstraction"""
    
    def test_realtime_transcriber_accepts_transcription_provider(self):
        """Test that RealtimeTranscriber can be initialized with any TranscriptionProvider"""
        mock_provider = MockTranscriptionProvider()
        mock_logger = Mock()
        transcriber = RealtimeTranscriber(mock_provider, mock_logger)
        
        assert transcriber.transcription_provider == mock_provider
        assert isinstance(transcriber.transcription_provider, TranscriptionProvider)
    
    @pytest.mark.asyncio
    async def test_start_realtime_transcription_uses_abstract_methods(self):
        """Test that start_realtime_transcription uses abstract methods from TranscriptionProvider"""
        mock_provider = MockTranscriptionProvider()
        mock_logger = Mock()
        transcriber = RealtimeTranscriber(mock_provider, mock_logger)
        
        # Mock the audio recorder to avoid actual recording
        transcriber.audio_recorder.start_recording = AsyncMock()
        transcriber.audio_recorder.stop_recording = AsyncMock()
        
        # Start a task to set session ready after initialization
        async def set_ready():
            await asyncio.sleep(0.1)
            await mock_provider.set_session_ready(True)
        
        # Create and manage the task properly
        task = asyncio.create_task(set_ready())
        
        try:
            # Start transcription
            await transcriber.start_realtime_transcription()
            
            # Verify that the abstract methods were called
            assert mock_provider.initialize_called, "initialize_session should have been called"
            assert mock_provider.start_listening_called, "start_listening should have been called"
        finally:
            # Ensure the task is properly cancelled and awaited
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    def test_transcription_provider_interface_compliance(self):
        """Test that OpenAiTranscriptionProvider properly implements TranscriptionProvider interface"""
        from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
        
        # Create a mock logger
        mock_logger = Mock()
        
        # Create provider with mock dependencies
        provider = OpenAiTranscriptionProvider("fake_api_key", mock_logger)
        
        # Verify it implements the abstract interface
        assert isinstance(provider, TranscriptionProvider)
        
        # Verify all required methods exist
        assert hasattr(provider, 'add_event_listener')
        assert hasattr(provider, 'remove_event_listener')
        assert hasattr(provider, 'clear_event_listeners')
        assert hasattr(provider, 'initialize_session')
        assert hasattr(provider, 'start_listening')
        assert hasattr(provider, 'send_audio_data')
        assert hasattr(provider, 'stop_listening')
        assert hasattr(provider, 'close')
    
    @pytest.mark.asyncio
    async def test_individual_transcription_provider_methods(self):
        """Test individual methods of the transcription provider"""
        mock_provider = MockTranscriptionProvider()
        
        # Test initialize_session
        result = await mock_provider.initialize_session()
        assert result is True
        assert mock_provider.initialized
        
        # Test start_listening
        result = await mock_provider.start_listening()
        assert result is True
        assert mock_provider.listening
        
        # Test close
        await mock_provider.close()
        assert mock_provider.closed 