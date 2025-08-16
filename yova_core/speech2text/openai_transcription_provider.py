#!/usr/bin/env python3

import asyncio
import json
import base64
import websockets
from openai import OpenAI
from typing import Dict, List, Callable, Any, Awaitable
from yova_core.core.event_emitter import EventEmitter
from yova_core.core.logging_utils import get_clean_logger
from yova_core.speech2text.transcription_provider import TranscriptionProvider
import logging

# WebSocket configuration
WEBSOCKET_URI = "wss://api.openai.com/v1/realtime"

# Audio format for API compatibility
FORMAT = "pcm16"
EXPLICIT_LANGUAGE = "pl"

# Turn detection configuration
TURN_DETECTION = {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 100,
    "silence_duration_ms": 200,
}

def get_session_config():
    """Get the session configuration for transcription"""
    return {
        "input_audio_format": FORMAT,
        "input_audio_transcription": {
            "model": "gpt-4o-transcribe",
            "prompt": "",
            "language": EXPLICIT_LANGUAGE
        },
        "turn_detection": TURN_DETECTION,
        "input_audio_noise_reduction": {
            "type": "near_field"
        },
        "include": [
            "item.input_audio_transcription.logprobs"
        ]
    }

class OpenAiTranscriptionProvider(TranscriptionProvider):
    def __init__(self, api_key, logger, websocket_uri=WEBSOCKET_URI, 
                 openai_client=None, websocket_connector=None):
        self.api_key = api_key
        self.websocket_uri = websocket_uri
        # Dependency injection for testability - fallback to default implementation
        self._openai_client = openai_client or OpenAI(api_key=api_key)
        self._websocket_connector = websocket_connector or websockets.connect
        self.websocket = None
        self.session_id = None
        self.logger = get_clean_logger("openai_transcription_provider", logger)
        self._logged_invalid_request = False
        # Use EventEmitter for event handling
        self.event_emitter = EventEmitter(logger)
        self._listening_task = None
        
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
    
    async def initialize_session(self) -> bool:
        """Initialize the transcription session"""
        try:
            self.logger.debug("Creating transcription session...")
            session_config = get_session_config()
            response = self._openai_client.beta.realtime.transcription_sessions.create(**session_config)
            self.logger.debug(f"Session created successfully, client_secret type: {type(response.client_secret)}")
            
            # Connect to WebSocket
            connected = await self.connect_websocket(response.client_secret)
            if not connected:
                self.logger.error("Failed to connect to WebSocket")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to create transcription session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def create_transcription_session(self):
        """Create a transcription session and get ephemeral token"""
        try:
            self.logger.debug("Creating transcription session...")
            session_config = get_session_config()
            response = self._openai_client.beta.realtime.transcription_sessions.create(**session_config)
            self.logger.debug(f"Session created successfully, client_secret type: {type(response.client_secret)}")
            return response.client_secret
        except Exception as e:
            self.logger.error(f"Failed to create transcription session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def connect_websocket(self, client_secret):
        """Connect to OpenAI's Realtime API WebSocket"""
        uri = f"{self.websocket_uri}?intent=transcription&client_secret={client_secret}"
        
        # Add authentication headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "openai-beta": "realtime=v1"
        }
        
        try:
            self.logger.debug(f"Connecting to WebSocket: {uri}")
            self.logger.debug(f"Headers: {headers}")
            self.websocket = await self._websocket_connector(uri, extra_headers=headers)
            self.logger.debug("WebSocket connection established")
            
            # Send session configuration
            session_config = {
                "type": "transcription_session.update",
                "session": get_session_config()
            }
            
            self.logger.debug("Sending session configuration...")
            await self.websocket.send(json.dumps(session_config))
            self.logger.debug("Session configuration sent")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_audio_data(self, audio_chunk):
        """Send audio data to the WebSocket"""
        if self.is_session_ready():
            # Reset the warning flag since we can now send data
            self._logged_invalid_request = False
            
            # Encode audio data as base64
            audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
            
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            
            try:
                await self.websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.error(f"WebSocket connection closed while sending audio: {e}")
                return False
            except Exception as e:
                self.logger.error(f"Error sending audio data: {e}")
                return False
        else:
            if not self._logged_invalid_request:
                self.logger.warning("Cannot send audio data: WebSocket not connected or session not ready")
                self._logged_invalid_request = True
            return False
        
        return True
    
    async def start_listening(self) -> bool:
        """Start listening for transcription events"""
        if not self.websocket:
            self.logger.error("Cannot start listening: WebSocket not connected")
            return False
            
        try:
            self._listening_task = asyncio.create_task(self.handle_websocket_messages())
            return True
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            return False
    
    async def stop_listening(self):
        """Stop listening for transcription events"""
        if self._listening_task:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
            self._listening_task = None
    
    async def handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    # Log all messages for debugging (can be commented out in production)
                    self.logger.debug(f"Received message type: {message_type}")
                    
                    # Emit the event to all registered listeners
                    await self._emit_event(message_type, data)
                    
                    # Handle specific message types for internal logic
                    if message_type == "input_audio_buffer.committed":
                        # Audio buffer was committed, can be used for ordering
                        item_id = data.get("item_id", "unknown")
                        self.logger.debug(f"Audio buffer committed - Item ID: {item_id}")
                        
                    elif message_type == "input_audio_buffer.speech_started":
                        # Speech started in audio buffer
                        self.logger.debug(f"Speech started - Item ID: {data.get('item_id', 'unknown')}")
                        
                    elif message_type == "input_audio_buffer.speech_stopped":
                        # Speech stopped in audio buffer
                        self.logger.debug(f"Speech stopped - Item ID: {data.get('item_id', 'unknown')}")
                        
                    elif message_type == "error":
                        error_data = data.get('error', {})
                        error_message = error_data.get('message', 'Unknown error')
                        error_type = error_data.get('type', 'unknown')
                        error_code = error_data.get('code', 'unknown')
                        self.logger.error(f"Type: {error_type}, Code: {error_code}, Message: {error_message}")
                        self.logger.error(f"Full error data: {json.dumps(error_data, indent=2)}")
                        
                    elif message_type == "transcription_session.created":
                        session_data = data.get('session', {})
                        self.session_id = session_data.get('id')
                        self.logger.debug(f"Session created with ID: {self.session_id}")
                        
                    elif message_type == "transcription_session.update":
                        self.logger.debug(f"Session updated: {data.get('status', 'unknown')}")
                        
                    elif message_type == "conversation.item.input_audio_transcription.delta":
                        # print the delta
                        self.logger.debug(f"Delta: {data['delta']}")

                    elif message_type == "conversation.item.input_audio_transcription.completed":
                        self.logger.debug(f"Transcription completed: {data['transcript']}")
                        await self._emit_event("transcription_completed", data['transcript'])

                    else:
                        # Log unknown message types
                        self.logger.debug(f"Unknown message type '{message_type}': {json.dumps(data, indent=2)}")
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse WebSocket message as JSON: {e}")
                    self.logger.error(f"Raw message: {message}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in WebSocket message handler: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    async def close(self):
        """Close the WebSocket connection"""
        await self.stop_listening()
        if self.websocket:
            await self.websocket.close()
    
    def get_session_id(self):
        """Get the current session ID"""
        return self.session_id
    
    def is_session_ready(self) -> bool:
        """Check if the transcription session is ready to receive audio data"""
        return self.websocket is not None and not self.websocket.closed and self.session_id is not None 