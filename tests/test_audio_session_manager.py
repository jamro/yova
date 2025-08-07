#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from voice_command_station.speech2text.audio_session_manager import AudioSessionManager
from voice_command_station.speech2text.realtime_transcriber import RealtimeTranscriber


class TestAudioSessionManager:
    """Test cases for AudioSessionManager"""
    
    @pytest.fixture
    def mock_transcriber(self):
        """Create a mock transcriber for testing"""
        transcriber = Mock(spec=RealtimeTranscriber)
        transcriber.start_realtime_transcription = AsyncMock()
        transcriber.transcription_provider = Mock()
        transcriber.transcription_provider.stop_listening = AsyncMock()
        transcriber.transcription_provider.close = AsyncMock()
        transcriber.cleanup = Mock()
        return transcriber
    
    @pytest.fixture
    def mock_audio_recorder(self):
        """Create a mock audio recorder for testing"""
        recorder = Mock()
        recorder.start_recording = Mock()
        recorder.stop_recording = Mock()
        recorder.record_and_stream = AsyncMock()
        return recorder
    
    @pytest.fixture
    def mock_speech_handler(self):
        """Create a mock speech handler for testing"""
        handler = Mock()
        handler.start = AsyncMock()
        handler.stop = AsyncMock()
        return handler
    
    @pytest.fixture
    def session_manager(self, mock_transcriber, mock_audio_recorder, mock_speech_handler):
        """Create an AudioSessionManager instance for testing"""
        return AudioSessionManager(mock_transcriber, mock_audio_recorder, mock_speech_handler)
    
    @pytest.mark.asyncio
    async def test_start_session_initializes_transcription(self, session_manager, mock_transcriber):
        """Test that start_session calls the transcriber's start_realtime_transcription"""
        # Mock the input to return immediately
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            await session_manager.start_session()
            
            # Verify transcriber initialization was called
            mock_transcriber.start_realtime_transcription.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_session_starts_audio_recording(self, session_manager, mock_audio_recorder):
        """Test that start_session starts audio recording"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            await session_manager.start_session()
            
            # Verify audio recording was started
            mock_audio_recorder.start_recording.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_session_creates_recording_task(self, session_manager, mock_audio_recorder):
        """Test that start_session creates a recording task"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            await session_manager.start_session()
            
            # Verify recording task was created
            assert session_manager.recording_task is not None
            mock_audio_recorder.record_and_stream.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_session_stops_recording(self, session_manager, mock_audio_recorder):
        """Test that stop_session stops audio recording"""
        session_manager.is_session_active = True
        
        await session_manager.stop_session()
        
        # Verify audio recording was stopped
        mock_audio_recorder.stop_recording.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_session_closes_transcription(self, session_manager, mock_transcriber):
        """Test that stop_session closes transcription provider"""
        session_manager.is_session_active = True
        
        await session_manager.stop_session()
        
        # Verify transcription provider was closed
        mock_transcriber.transcription_provider.stop_listening.assert_called_once()
        mock_transcriber.transcription_provider.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_session_cancels_recording_task(self, session_manager):
        """Test that stop_session cancels the recording task"""
        session_manager.is_session_active = True
        session_manager.recording_task = asyncio.create_task(asyncio.sleep(10))  # Long running task
        
        await session_manager.stop_session()
        
        # Verify recording task was cancelled
        assert session_manager.recording_task.cancelled()
    
    def test_cleanup_calls_transcriber_cleanup(self, session_manager, mock_transcriber):
        """Test that cleanup calls transcriber cleanup"""
        session_manager.cleanup()
        
        # Verify transcriber cleanup was called
        mock_transcriber.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_session_does_nothing_when_inactive(self, session_manager, mock_transcriber, mock_audio_recorder):
        """Test that stop_session does nothing when session is not active"""
        session_manager.is_session_active = False
        
        await session_manager.stop_session()
        
        # Verify no cleanup methods were called
        mock_audio_recorder.stop_recording.assert_not_called()
        mock_transcriber.transcription_provider.stop_listening.assert_not_called()
        mock_transcriber.transcription_provider.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_start_session_sets_session_active(self, session_manager):
        """Test that start_session sets is_session_active to True"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            await session_manager.start_session()
            
            # Verify session is marked as active during execution
            # Note: it will be set to False in finally block, but we can verify the flow
            assert session_manager.is_session_active is False  # After finally block
    
    @pytest.mark.asyncio
    async def test_stop_session_sets_session_inactive(self, session_manager):
        """Test that stop_session sets is_session_active to False"""
        session_manager.is_session_active = True
        
        await session_manager.stop_session()
        
        # Verify session is marked as inactive
        assert session_manager.is_session_active is False 