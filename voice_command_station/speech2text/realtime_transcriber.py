#!/usr/bin/env python3

import asyncio
from voice_command_station.speech2text.transcription_provider import TranscriptionProvider
from voice_command_station.speech2text.audio_recorder import AudioRecorder
from typing import Dict, List, Callable, Any, Awaitable
from voice_command_station.core.event_emitter import EventEmitter
from voice_command_station.core.logging_utils import get_clean_logger
import logging

class RealtimeTranscriber:
    def __init__(self, transcription_provider: TranscriptionProvider, audio_recorder: AudioRecorder, logger=None, onCompleted=None):
        self.transcription_provider: TranscriptionProvider = transcription_provider
        self.audio_recorder: AudioRecorder = audio_recorder
        self.logger = get_clean_logger("realtime_transcriber", logger)
        
        # Use EventEmitter for domain-specific event handling
        self.event_emitter = EventEmitter(self.logger)
        
        # Set up internal transcription provider event handlers
        self._setup_transcription_provider_handlers()
        
        # Set up audio recorder event handlers
        self._setup_audio_recorder_handlers()
        
        # Add event listener for transcription completion if callback provided
        if onCompleted:
            self.add_event_listener("transcription_completed", lambda data: onCompleted(data['transcript']))
    
    def _setup_transcription_provider_handlers(self):
        """Set up internal handlers for transcription provider events"""
        self.transcription_provider.add_event_listener(
            "transcription_completed",
            self._on_transcription_completed
        )
        self.transcription_provider.add_event_listener(
            "error",
            self._on_transcription_error
        )
    
    def _setup_audio_recorder_handlers(self):
        """Set up internal handlers for AudioRecorder events"""
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
    
    async def start_realtime_transcription(self):
        """Initialize and start real-time transcription session"""
        try:
            # Initialize transcription session
            initialized = await self.transcription_provider.initialize_session()
            if not initialized:
                raise Exception("Failed to initialize transcription session")
            
            # Start listening for transcription events
            listening_started = await self.transcription_provider.start_listening()
            if not listening_started:
                raise Exception("Failed to start listening for transcription events")
            
            # Wait for session to be fully ready
            max_wait_time = 10  # seconds
            wait_interval = 0.1  # seconds
            waited_time = 0
            
            while not self.transcription_provider.is_session_ready() and waited_time < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            if not self.transcription_provider.is_session_ready():
                raise Exception("Session not ready within timeout period")
            
            self.logger.info("Transcription session ready")
            
        except Exception as e:
            self.logger.error(f"Error during real-time transcription initialization: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources"""
        self.audio_recorder.cleanup()
        if self.transcription_provider:
            asyncio.create_task(self.transcription_provider.close()) 