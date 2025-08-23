#!/usr/bin/env python3

import asyncio
from yova_core.speech2text.transcription_provider import TranscriptionProvider
from yova_core.speech2text.audio_recorder import AudioRecorder
from typing import Dict, List, Callable, Any, Awaitable
from yova_shared import EventEmitter
from yova_shared import get_clean_logger
import logging

class RealtimeTranscriber:
    def __init__(self, transcription_provider: TranscriptionProvider, logger=None, onCompleted=None, 
                 max_wait_time=10, wait_interval=0.1, prerecord_beep="beep7.wav", audio_logs_path=None):
        self.transcription_provider: TranscriptionProvider = transcription_provider
        self.audio_recorder: AudioRecorder = AudioRecorder(logger)
        self.audio_recorder.prerecord_beep = prerecord_beep
        self.audio_recorder.audio_logs_path = audio_logs_path or None
        self.logger = get_clean_logger("realtime_transcriber", logger)
        
        # Configuration parameters for testing
        self.max_wait_time = max_wait_time  # seconds
        self.wait_interval = wait_interval  # seconds
        
        # State management for easier testing
        self._is_initialized = False
        self._is_listening = False
        self._is_session_ready = False
        
        # Use EventEmitter for domain-specific event handling
        self.event_emitter = EventEmitter(self.logger)
        
        # Set up event handlers
        self.setup_event_handlers()
        
        # Add event listener for transcription completion if callback provided
        if onCompleted:
            self.add_event_listener("transcription_completed", lambda data: onCompleted(data['transcript']))
    
    @property
    def is_initialized(self) -> bool:
        """Check if the transcription session has been initialized"""
        return self._is_initialized
    
    @property
    def is_listening(self) -> bool:
        """Check if the transcription session is currently listening"""
        return self._is_listening
    
    @property
    def is_session_ready(self) -> bool:
        """Check if the transcription session is ready to receive audio data"""
        return self._is_session_ready
    
    @property
    def is_active(self) -> bool:
        """Check if the transcription session is fully active (initialized, listening, and ready)"""
        return self._is_initialized and self._is_listening and self._is_session_ready

    def setup_event_handlers(self):
        """Set up all event handlers for transcription provider and audio recorder.
        This method can be called independently for testing purposes."""

        self.transcription_provider.add_event_listener(
            "transcription_completed",
            self._on_transcription_completed
        )
        self.transcription_provider.add_event_listener(
            "error",
            self._on_transcription_error
        )
    
        self.audio_recorder.add_event_listener(
            "audio_chunk",
            self._on_audio_chunk
        )
    
    async def _on_audio_chunk(self, data):
        """Handle audio chunk event from AudioRecorder and forward to transcription provider"""
        audio_data = data.get("audio_data")
        if audio_data:
            success = await self.transcription_provider.send_audio_data(audio_data)
            if not success:
                # Don't stop recording immediately on first failure
                # The session might still be initializing
                self.logger.warning("Failed to send audio data to transcription provider, will retry on next chunk")
    
    async def _on_transcription_completed(self, data):
        """Handle transcription completed event"""
        await self._emit_event("transcription_completed", {
            "transcript": data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def _on_transcription_error(self, data):
        """Handle transcription error event"""
        await self._emit_event("error", {
            "error": data.get("error", "Unknown error"),
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """Add an event listener for a specific event type"""
        self.event_emitter.add_event_listener(event_type, listener)
    
    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """Remove an event listener for a specific event type"""
        self.event_emitter.remove_event_listener(event_type, listener)
    
    def clear_event_listeners(self, event_type: str = None):
        """Clear all event listeners or listeners for a specific event type"""
        self.event_emitter.clear_event_listeners(event_type)
    
    async def _emit_event(self, event_type: str, data: Any):
        """Emit an event to all registered listeners"""
        await self.event_emitter.emit_event(event_type, data)
    
    async def _wait_for_session_ready(self) -> bool:
        """Wait for the transcription session to be ready using configurable timing parameters.
        
        Returns:
            bool: True if session is ready within timeout, False otherwise
        """
        waited_time = 0
        
        while not self.transcription_provider.is_session_ready() and waited_time < self.max_wait_time:
            await asyncio.sleep(self.wait_interval)
            waited_time += self.wait_interval
        
        return self.transcription_provider.is_session_ready()
    
    async def start_audio_recording(self):
        await self.audio_recorder.start_recording()
        self.logger.info("Audio recorder started")

    async def stop_audio_recording(self):
        await self.audio_recorder.stop_recording()
        self.logger.info("Audio recorder stopped")
        
    async def start_realtime_transcription(self):
        """Initialize and start real-time transcription session"""
        try:

            # Initialize transcription session
            initialized = await self.transcription_provider.initialize_session()
            if not initialized:
                raise Exception("Failed to initialize transcription session")
            
            self._is_initialized = True
            self.logger.info("Transcription session initialized")
            
            # Start listening for transcription events
            listening_started = await self.transcription_provider.start_listening()
            if not listening_started:
                raise Exception("Failed to start listening for transcription events")
            
            self._is_listening = True
            self.logger.info("Transcription session listening started")
            
            # Wait for session to be fully ready
            session_ready = await self._wait_for_session_ready()
            if not session_ready:
                raise Exception("Session not ready within timeout period")
            
            self._is_session_ready = True
            self.logger.info("Transcription session ready")

            
        except Exception as e:
            self.logger.error(f"Error during real-time transcription initialization: {e}")
            # Reset states on error
            self._is_initialized = False
            self._is_listening = False
            self._is_session_ready = False
            raise
        
    async def stop_realtime_transcription(self):
        """Stop real-time transcription session"""
        await self.transcription_provider.stop_listening()
        await self.transcription_provider.close()
    
    def cleanup(self):
        """Clean up resources"""
        self.audio_recorder.cleanup()
        if self.transcription_provider:
            asyncio.create_task(self.transcription_provider.close())
        
        # Reset states after cleanup
        self._is_initialized = False
        self._is_listening = False
        self._is_session_ready = False 