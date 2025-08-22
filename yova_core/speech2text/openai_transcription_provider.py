#!/usr/bin/env python3

import asyncio
import json
import base64
import websockets
from openai import OpenAI
from typing import Dict, List, Callable, Any, Awaitable
from yova_shared import EventEmitter
from yova_shared import get_clean_logger
from yova_core.speech2text.transcription_provider import TranscriptionProvider
from yova_core.speech2text.audio_buffer import AudioBuffer
import logging
import numpy as np

# WebSocket configuration
WEBSOCKET_URI = "wss://api.openai.com/v1/realtime"

# Audio format for API compatibility
FORMAT = "pcm16"
EXPLICIT_LANGUAGE = "pl"
SILENCE_AMPLITUDE_THRESHOLD = 0.15
SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
MIN_SPEECH_LENGTH = 0.5

# Turn detection configuration
TURN_DETECTION = None

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

def get_audio_amplitude(audio_chunk):
    if not audio_chunk:
        return None

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0
    
    max_amplitude = np.max(np.abs(audio_array))
    return max_amplitude / 32768.0

def get_audio_len(audio_chunk): # returns length in seconds
    if not audio_chunk:
        return 0

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0

    seconds = len(audio_array) / (SAMPLE_RATE * AUDIO_CHANNELS)
    return seconds

class OpenAiTranscriptionProvider(TranscriptionProvider):
    def __init__(self, api_key, logger, websocket_uri=WEBSOCKET_URI, 
                 openai_client=None, websocket_connector=None, audio_buffer=None):
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
        self._is_buffer_empty = True
        self._buffer_length = 0
        # Audio chunk buffer for when session is not ready
        self._audio_buffer = audio_buffer or AudioBuffer(self.logger, SAMPLE_RATE, AUDIO_CHANNELS)
        
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
            self.logger.info("Creating transcription session...")
            session_config = get_session_config()
            response = self._openai_client.beta.realtime.transcription_sessions.create(**session_config)
            self.logger.info(f"Session created successfully, client_secret type: {type(response.client_secret)}")
            
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
            self.logger.info("Creating transcription session...")
            session_config = get_session_config()
            response = self._openai_client.beta.realtime.transcription_sessions.create(**session_config)
            self.logger.info(f"Session created successfully, client_secret type: {type(response.client_secret)}")
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
            self.logger.info(f"Connecting to WebSocket: {uri}")
            self.logger.info(f"Headers: {headers}")
            self.websocket = await self._websocket_connector(uri, extra_headers=headers)
            self.logger.info("WebSocket connection established")
            
            # Send session configuration
            session_config = {
                "type": "transcription_session.update",
                "session": get_session_config()
            }
            
            self.logger.info("Sending session configuration...")
            await self.websocket.send(json.dumps(session_config))
            self.logger.info("Session configuration sent")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    async def _send_to_websocket(self, message, content_label="data"):
        """Send a message to the WebSocket"""
        if not self.websocket or self.websocket.closed:
            self.logger.error(f"Cannot send {content_label}: WebSocket not connected or closed")
            return False
            
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed while sending {content_label}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending {content_label}: {e}")
            return False
    
    async def send_audio_data(self, audio_chunk):
        """Send audio data to the WebSocket"""
        if self.is_session_ready():
            # Reset the warning flag since we can now send data
            self._logged_invalid_request = False

            # Flush any buffered audio chunks first
            if self._audio_buffer.has_buffered_audio():
                await self._flush_buffered_audio_chunks()

            amplitude = get_audio_amplitude(audio_chunk)
            if amplitude > SILENCE_AMPLITUDE_THRESHOLD and self._is_buffer_empty:
                self.logger.info("Speech detected")
                self._is_buffer_empty = False

            self._buffer_length += get_audio_len(audio_chunk)
            self.logger.info(f"Buffer length: {self._buffer_length}")

            # Encode audio data as base64
            audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
            
            if not await self._send_to_websocket({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }, 'audio_data'):
                return False
            
        else:
            # Session not ready, buffer the audio chunk
            self._audio_buffer.add_audio_chunk(audio_chunk)
            
            if not self._logged_invalid_request:
                self.logger.warning("Cannot send audio data: WebSocket not connected or session not ready. Audio chunks are being buffered.")
                self._logged_invalid_request = True
            return True  # Return True since we're successfully buffering
        
        return True
    
    async def _flush_buffered_audio_chunks(self):
        """Flush all buffered audio chunks to the WebSocket"""
        if not self._audio_buffer.has_buffered_audio():
            return True
            
        if not self.is_session_ready():
            self.logger.warning("Cannot flush buffered audio chunks: session not ready")
            return False
            
        buffered_info = self._audio_buffer.get_buffered_audio_info()
        self.logger.info(f"Flushing {buffered_info['chunk_count']} buffered audio chunks (total length: {buffered_info['total_length']:.2f}s)")
        
        try:
            buffered_chunks = self._audio_buffer.get_buffered_chunks()
            for i, audio_chunk in enumerate(buffered_chunks):
                # Encode audio data as base64
                audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
                
                if not await self._send_to_websocket({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }, f'buffered_audio_data_{i+1}'):
                    self.logger.error(f"Failed to send buffered audio chunk {i+1}/{len(buffered_chunks)}")
                    return False
            
            # Clear the buffer after successful flush
            self._audio_buffer.clear_buffer()
            self.logger.info("Successfully flushed all buffered audio chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error flushing buffered audio chunks: {e}")
            return False
    
    def has_buffered_audio(self) -> bool:
        """Check if there are buffered audio chunks waiting to be sent"""
        return self._audio_buffer.has_buffered_audio()
    
    def get_buffered_audio_info(self) -> dict:
        """Get information about buffered audio chunks"""
        buffer_info = self._audio_buffer.get_buffered_audio_info()
        buffer_info['is_session_ready'] = self.is_session_ready()
        return buffer_info
    
    def clear_audio_buffer(self):
        """Clear the audio chunk buffer (useful for cleanup or reset scenarios)"""
        self._audio_buffer.clear_buffer()
    
    async def flush_audio_buffer(self) -> bool:
        """Manually flush the audio buffer if session is ready"""
        if not self.has_buffered_audio():
            self.logger.info("No buffered audio to flush")
            return True
            
        if not self.is_session_ready():
            self.logger.warning("Cannot flush audio buffer: session not ready")
            return False
            
        return await self._flush_buffered_audio_chunks()
    
    async def start_listening(self) -> bool:
        """Start listening for transcription events"""

        if not self.websocket:
            self.logger.error("Cannot start listening: WebSocket not connected")
            return False
        
        if self._listening_task:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
            self._listening_task = None
            
        try:
            self._is_buffer_empty = True
            self._buffer_length = 0
            self._listening_task = asyncio.create_task(self.handle_websocket_messages())

            if not await self._send_to_websocket({
                "type": "input_audio_buffer.clear"
            }, 'audio_data'):
                return False

            return True
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            return False
    
    async def stop_listening(self):
        """Stop listening for transcription events"""

        if not self._is_buffer_empty and self._buffer_length >= MIN_SPEECH_LENGTH:
            if not await self._send_to_websocket({
                "type": "input_audio_buffer.commit"
            }, 'input_audio_buffer.commit'):
                return False
        elif self._listening_task:
            self._listening_task.cancel()
            self._listening_task = None
            await self._emit_event("transcription_completed", '')
        
        if self._listening_task:
            await self._listening_task

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
                    self.logger.info(f"Received message type: {message_type}")
                    
                    # Emit the event to all registered listeners
                    await self._emit_event(message_type, data)
                    
                    # Handle specific message types for internal logic
                    if message_type == "input_audio_buffer.committed":
                        # Audio buffer was committed, can be used for ordering
                        item_id = data.get("item_id", "unknown")
                        self.logger.info(f"Audio buffer committed - Item ID: {item_id}")
                        
                    elif message_type == "input_audio_buffer.speech_started":
                        # Speech started in audio buffer
                        self.logger.info(f"Speech started - Item ID: {data.get('item_id', 'unknown')}")
                        
                    elif message_type == "input_audio_buffer.speech_stopped":
                        # Speech stopped in audio buffer
                        self.logger.info(f"Speech stopped - Item ID: {data.get('item_id', 'unknown')}")
                        
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
                        self.logger.info(f"Session created with ID: {self.session_id}")
                        
                        # Flush any buffered audio chunks now that session is ready
                        if self._audio_buffer.has_buffered_audio():
                            self.logger.info("Session ready, flushing buffered audio chunks...")
                            await self._flush_buffered_audio_chunks()
                        else:
                            self.logger.info("No buffered audio to flush, session is ready")
                        
                    elif message_type == "transcription_session.update":
                        self.logger.info(f"Session updated: {data.get('status', 'unknown')}")
                        
                    elif message_type == "conversation.item.input_audio_transcription.delta":
                        # print the delta
                        self.logger.info(f"Delta: {data['delta']}")

                    elif message_type == "conversation.item.input_audio_transcription.completed":
                        self.logger.info(f"Transcription completed: {data['transcript']}")
                        await self._emit_event("transcription_completed", data['transcript'])
                        self._listening_task = None
                        return

                    else:
                        # Log unknown message types
                        self.logger.info(f"Unknown message type '{message_type}': {json.dumps(data, indent=2)}")
                        
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

        if self._listening_task:
            await self._listening_task
            self._listening_task = None

        # Clear any buffered audio chunks
        if self._audio_buffer.has_buffered_audio():
            self.logger.info("Clearing audio buffer before closing")
            self.clear_audio_buffer()

        if self.websocket:
            await self.websocket.close()
    
    def get_session_id(self):
        """Get the current session ID"""
        return self.session_id
    
    def is_session_ready(self) -> bool:
        """Check if the transcription session is ready to receive audio data"""
        return self.websocket is not None and not self.websocket.closed and self.session_id is not None 