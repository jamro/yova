#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable, Optional
from yova_shared import EventSource

class TranscriptionProvider(EventSource):
    """Abstract base class for transcription providers"""
    
    @abstractmethod
    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """Add an event listener for a specific event type"""
        pass
    
    @abstractmethod
    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        """Remove an event listener for a specific event type"""
        pass
    
    @abstractmethod
    def clear_event_listeners(self, event_type: str = None):
        """Clear all event listeners or listeners for a specific event type"""
        pass
    
    @abstractmethod
    async def initialize_session(self) -> bool:
        """Initialize the transcription session"""
        pass
    
    @abstractmethod
    async def start_listening(self) -> bool:
        """Start listening for transcription events"""
        pass
    
    @abstractmethod
    async def send_audio_data(self, audio_chunk: bytes) -> bool:
        """Send audio data to the transcription provider"""
        pass
    
    @abstractmethod
    async def stop_listening(self):
        """Stop listening for transcription events"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the transcription session and cleanup resources"""
        pass
    
    @abstractmethod
    def is_session_ready(self) -> bool:
        """Check if the transcription session is ready to receive audio data"""
        pass 