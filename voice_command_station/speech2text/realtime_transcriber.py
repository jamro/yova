#!/usr/bin/env python3

import asyncio
from voice_command_station.speech2text.websocket_handler import WebSocketHandler
from voice_command_station.speech2text.audio_recorder import AudioRecorder
from typing import Dict, List, Callable, Any, Awaitable
from voice_command_station.core.event_emitter import EventEmitter
from voice_command_station.core.logging_utils import get_clean_logger
import logging

class RealtimeTranscriber:
    def __init__(self, api_key, logger=None, onCompleted=None):
        self.api_key = api_key
        self.logger = get_clean_logger("realtime_transcriber", logger)
        self.websocket_handler = WebSocketHandler(api_key, self.logger)
        self.audio_recorder = AudioRecorder(self.logger)
        
        # Use EventEmitter for domain-specific event handling
        self.event_emitter = EventEmitter(self.logger)
        
        # Set up internal WebSocket event handlers
        self._setup_websocket_handlers()
        
        # Set up audio recorder event handlers
        self._setup_audio_recorder_handlers()
        
        # Add event listener for transcription completion if callback provided
        if onCompleted:
            self.add_event_listener("transcription_completed", lambda data: onCompleted(data['transcript']))
    
    def _setup_websocket_handlers(self):
        """Set up internal handlers for WebSocket events"""
        self.websocket_handler.add_event_listener(
            "conversation.item.input_audio_transcription.completed",
            self._on_websocket_transcription_completed
        )
        self.websocket_handler.add_event_listener(
            "conversation.item.input_audio_transcription.delta",
            self._on_websocket_transcription_delta
        )
        self.websocket_handler.add_event_listener(
            "input_audio_buffer.speech_started",
            self._on_websocket_speech_started
        )
        self.websocket_handler.add_event_listener(
            "input_audio_buffer.speech_stopped",
            self._on_websocket_speech_stopped
        )
        self.websocket_handler.add_event_listener(
            "transcription_session.created",
            self._on_websocket_session_created
        )
        self.websocket_handler.add_event_listener(
            "error",
            self._on_websocket_error
        )
    
    def _setup_audio_recorder_handlers(self):
        """Set up internal handlers for AudioRecorder events"""
        self.audio_recorder.add_event_listener(
            "audio_chunk",
            self._on_audio_chunk
        )
    
    async def _on_audio_chunk(self, data):
        """Handle audio chunk event from AudioRecorder and forward to WebSocketHandler"""
        audio_data = data.get("audio_data")
        if audio_data:
            success = await self.websocket_handler.send_audio_data(audio_data)
            if not success:
                self.logger.error("Failed to send audio data to WebSocket, stopping recording")
                self.audio_recorder.stop_recording()
    
    async def _on_websocket_transcription_completed(self, data):
        """Handle WebSocket transcription completed event"""
        await self._emit_event("transcription_completed", {
            "transcript": data.get("transcript", ""),
            "item_id": data.get("item_id"),
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def _on_websocket_transcription_delta(self, data):
        """Handle WebSocket transcription delta event"""
        delta = data.get("delta", "")
        if delta.strip():
            await self._emit_event("transcription_progress", {
                "delta": delta,
                "item_id": data.get("item_id"),
                "timestamp": asyncio.get_event_loop().time()
            })
    
    async def _on_websocket_speech_started(self, data):
        """Handle WebSocket speech started event"""
        await self._emit_event("speech_detected", {
            "item_id": data.get("item_id"),
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def _on_websocket_speech_stopped(self, data):
        """Handle WebSocket speech stopped event"""
        await self._emit_event("speech_ended", {
            "item_id": data.get("item_id"),
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def _on_websocket_session_created(self, data):
        """Handle WebSocket session created event"""
        self.session_id = data.get("session_id")
        await self._emit_event("session_ready", {
            "session_id": self.session_id,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def _on_websocket_error(self, data):
        """Handle WebSocket error event"""
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
        """Start real-time transcription"""
        try:
            # Create transcription session
            client_secret = await self.websocket_handler.create_transcription_session()
            if not client_secret:
                raise Exception("Failed to create transcription session")
            
            # Connect to WebSocket
            connected = await self.websocket_handler.connect_websocket(client_secret)
            if not connected:
                raise Exception("Failed to connect to WebSocket")
            
            # Start listening for WebSocket messages
            websocket_task = asyncio.create_task(self.websocket_handler.handle_websocket_messages())
            
            # Start recording audio
            self.audio_recorder.start_recording()
            recording_task = asyncio.create_task(self.audio_recorder.record_and_stream())
            
            # Wait for user input to stop
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # Stop recording and cleanup
            self.audio_recorder.stop_recording()
            recording_task.cancel()
            websocket_task.cancel()
            
            # Close WebSocket connection
            await self.websocket_handler.close()
            
        except Exception as e:
            self.logger.error(f"Error during real-time transcription: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources"""
        self.audio_recorder.cleanup()
        if self.websocket_handler:
            asyncio.create_task(self.websocket_handler.close()) 