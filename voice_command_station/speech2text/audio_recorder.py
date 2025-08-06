#!/usr/bin/env python3

import pyaudio
import asyncio
from typing import Dict, List, Callable, Any, Awaitable, Optional
from voice_command_station.core.event_emitter import EventEmitter

# Audio recording parameters
CHUNK = 512  # Smaller chunk size for more frequent updates
CHANNELS = 1
RATE = 16000

class AudioRecorder:
    def __init__(self, logger, pyaudio_instance=None, stream_factory=None):
        """
        Initialize AudioRecorder with optional dependency injection for testing.
        
        Args:
            logger: Logger instance for debugging
            pyaudio_instance: Optional PyAudio instance for dependency injection (for testing)
            stream_factory: Optional factory function for creating audio streams (for testing)
        """
        # Use dependency injection for testability, fallback to default implementation
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self._stream_factory = stream_factory or self._create_default_stream
        self.logger = logger
        self.is_recording = False
        self.stream = None
        # Use EventEmitter for event handling
        self.event_emitter = EventEmitter(logger)
        
    def _create_default_stream(self, pyaudio_instance, **kwargs):
        """Default factory method for creating audio streams"""
        return pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            **kwargs
        )
        
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
    
    def _create_stream(self):
        """Create audio stream using the configured factory"""
        return self._stream_factory(self._pyaudio_instance)
        
    async def record_and_stream(self):
        """Record audio and emit chunk events"""
        try:
            self.stream = self._create_stream()
            
            self.logger.info("Recording and streaming... Press Enter to stop")
            
            while self.is_recording:
                try:
                    audio_chunk = self.stream.read(CHUNK, exception_on_overflow=False)
                    # Emit audio chunk event instead of directly calling websocket handler
                    await self._emit_event("audio_chunk", {
                        "audio_data": audio_chunk,
                        "chunk_size": len(audio_chunk),
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    await asyncio.sleep(0.02)  # Slightly longer delay to prevent overwhelming the API
                except Exception as e:
                    if self.is_recording:  # Only print error if we're still supposed to be recording
                        self.logger.error(f"Error during audio streaming: {e}")
                    break
        except Exception as e:
            self.logger.error(f"Error during recording: {e}")
        finally:
            self._cleanup_stream()
    
    def _cleanup_stream(self):
        """Clean up the audio stream"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
    
    def start_recording(self):
        """Start recording"""
        self.is_recording = True
    
    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        self._cleanup_stream()
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_recording()
        self._pyaudio_instance.terminate() 