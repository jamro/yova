#!/usr/bin/env python3

import asyncio
from typing import Optional, Callable, Any, Awaitable
from voice_command_station.speech2text.audio_recorder import AudioRecorder
from voice_command_station.speech2text.realtime_transcriber import RealtimeTranscriber
from voice_command_station.core.logging_utils import get_clean_logger


class AudioSessionManager:
    """
    Manages the lifecycle of an audio recording session, coordinating between
    the audio recorder and real-time transcriber.
    """
    
    def __init__(self, transcriber: RealtimeTranscriber, audio_recorder: AudioRecorder, logger=None):
        self.transcriber = transcriber
        self.audio_recorder = audio_recorder
        self.logger = get_clean_logger("audio_session_manager", logger)
        self.recording_task: Optional[asyncio.Task] = None
        self.is_session_active = False
    
    async def start_session(self):
        """
        Start the audio recording session with real-time transcription.
        This method handles the complete lifecycle of the session.
        """
        try:
            self.logger.info("Starting audio session...")
            self.is_session_active = True
            
            # Initialize and start the transcription session
            await self.transcriber.start_realtime_transcription()
            
            # Start recording audio
            self.audio_recorder.start_recording()
            self.recording_task = asyncio.create_task(
                self.audio_recorder.record_and_stream()
            )
            
            self.logger.info("Audio session started. Press Enter to stop...")
            
            # Wait for user input to stop
            await asyncio.get_event_loop().run_in_executor(None, input)
            
        except Exception as e:
            self.logger.error(f"Error during audio session: {e}")
            raise
        finally:
            await self.stop_session()
    
    async def stop_session(self):
        """Stop the audio recording session and cleanup resources."""
        if not self.is_session_active:
            return
            
        self.logger.info("Stopping audio session...")
        self.is_session_active = False
        
        # Stop recording
        if self.audio_recorder:
            self.audio_recorder.stop_recording()
        
        # Cancel recording task if it exists
        if self.recording_task and not self.recording_task.done():
            self.recording_task.cancel()
            try:
                await self.recording_task
            except asyncio.CancelledError:
                pass
        
        # Stop transcription
        if self.transcriber.transcription_provider:
            await self.transcriber.transcription_provider.stop_listening()
            await self.transcriber.transcription_provider.close()
        
        self.logger.info("Audio session stopped.")
    
    def cleanup(self):
        """Clean up all resources."""
        if self.transcriber:
            self.transcriber.cleanup() 