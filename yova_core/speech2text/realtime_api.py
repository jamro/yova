from yova_shared import get_clean_logger
import websockets
import json
from openai import OpenAI
import base64
import asyncio

# WebSocket configuration
WEBSOCKET_URI = "wss://api.openai.com/v1/realtime"

# Audio format for API compatibility
FORMAT = "pcm16"

class RealtimeApi:
    
    def __init__(self, api_key, logger, openai_client=None, websocket_connector=None, 
                 model="gpt-4o-transcribe", language="en", noise_reduction="near_field", instructions=""):
        self.logger = get_clean_logger("realtime_api", logger)
        self._openai_client = openai_client or OpenAI(api_key=api_key)
        self._websocket_connector = websocket_connector or websockets.connect
        self.websocket = None
        self.session_id = None
        self.api_key = api_key
        self.model = model
        self.language = language
        self.noise_reduction = noise_reduction
        self.instructions = instructions
        self.session_start_time = None
        self.last_activity_time = None
        
    async def connect(self):
        """Connect to OpenAI's Realtime API"""
        self.logger.info(f"Connecting to OpenAI Realtime API...")
        self.session_start_time = None
        self.last_activity_time = asyncio.get_event_loop().time()
        
        # Stage 1: Create transcription session for authentication purposes
        client_secret = self._create_transcription_session(self.model, self.language, self.noise_reduction)
        if not client_secret:
            self.logger.error("Failed to create transcription session")
            return False
        
        # Stage 2: Connect to the WebSocket
        connected = await self._connect_websocket(client_secret)
        if not connected:
            self.logger.error("Failed to connect to WebSocket")
            return False
        
        # Stage 3: Handle WebSocket messages
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            self.logger.debug(f"Received message type: {message_type}")

            if message_type == "transcription_session.created":
                session_data = data.get('session', {})
                self.session_id = session_data.get('id')
                self.logger.info(f"Session created with ID: {self.session_id}")
                self.session_start_time = asyncio.get_event_loop().time()
                self.last_activity_time = self.session_start_time
                return True
            elif message_type == "error":
                error_data = data.get('error', {})
                error_message = error_data.get('message', 'Unknown error')
                error_type = error_data.get('type', 'unknown')
                error_code = error_data.get('code', 'unknown')
                self.logger.error(f"Unable to create session for Realtime API")
                self.logger.error(f"Type: {error_type}, Code: {error_code}, Message: {error_message}")
                self.logger.error(f"Full error data: {json.dumps(error_data, indent=2)}")
                return False
            
        self.logger.info("WebSocket connection closed unexpectedly. No session created.")
        return False
    
    async def disconnect(self):
        """Disconnect from OpenAI's Realtime API"""
        self.logger.info("Disconnecting from OpenAI Realtime API...")
        if self.websocket:
            await self.websocket.close()
        self.websocket = None
        self.session_id = None
        self.session_start_time = None

    @property
    def is_connected(self):
        return self.websocket is not None and not self.websocket.closed and self.session_id is not None

    async def send(self, message, log_label="data", exception_on_error=True):
        if not self.is_connected:
            self.logger.error("Cannot send message: WebSocket not connected or session not created")
            if exception_on_error:
                raise Exception("WebSocket not connected or session not created")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            self.last_activity_time = asyncio.get_event_loop().time()
            return True
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed while sending {log_label}: {e}")
            if exception_on_error:
                raise Exception("WebSocket connection closed while sending message")
            return False
        except Exception as e:
            self.logger.error(f"Error sending {log_label}: {e}")
            if exception_on_error:
                raise Exception(f"Error sending {log_label}: {e}")
            return False
        
    async def get_message(self):
        if not self.is_connected:
            self.logger.error("Cannot get message: WebSocket not connected or session not created")
            return None
        
        return await self.websocket.recv()
    
    async def send_audio_chunk(self, audio_chunk, exception_on_error=True):
        audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
        message = {"type": "input_audio_buffer.append", "audio": audio_base64}
        return await self.send(message, 'audio_buffer.append', exception_on_error)
    
    async def clear_audio_buffer(self, exception_on_error=True):
        message = {"type": "input_audio_buffer.clear"}
        return await self.send(message, 'audio_buffer.clear', exception_on_error)
    
    async def commit_audio_buffer(self, exception_on_error=True):
        message = {"type": "input_audio_buffer.commit"}
        # clear the message queue
        while self.get_message_queue_length() > 0: 
            await self.get_message()

        # send the message
        result = await self.send(message, 'audio_buffer.commit', exception_on_error)
        if not result:
            self.logger.error("Failed to commit audio buffer")
            return ''

        # wait for the transcription to complete
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            self.logger.debug(f"Received message type: {message_type}")

            if message_type == "error":
                error_data = data.get('error', {})
                error_message = error_data.get('message', 'Unknown error')
                error_type = error_data.get('type', 'unknown')
                error_code = error_data.get('code', 'unknown')
                self.logger.error(f"Type: {error_type}, Code: {error_code}, Message: {error_message}")
                self.logger.error(f"Full error data: {json.dumps(error_data, indent=2)}")
                return ''
            elif message_type == "conversation.item.input_audio_transcription.completed":
                self.logger.info(f"Transcription completed: {data['transcript']}")
                return data.get("transcript")
            
        self.logger.error("Commit audio without transcription")
        return ''
    
    async def query_error(self):
        while self.get_message_queue_length() > 0:
            self.last_activity_time = asyncio.get_event_loop().time()
            message = await self.get_message()
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            self.logger.debug(f"Received message type: {message_type}")

            if message_type == "error":
                error_data = data.get('error', {})
                error_message = error_data.get('message', 'Unknown error')
                error_type = error_data.get('type', 'unknown')
                error_code = error_data.get('code', 'unknown')
                self.logger.error(f"Type: {error_type}, Code: {error_code}, Message: {error_message}")
                self.logger.error(f"Full error data: {json.dumps(error_data, indent=2)}")
                return error_message
            
        return None
    
    
    def get_message_queue_length(self):
        if not self.is_connected:
            self.logger.error("Cannot get message queue length: WebSocket not connected or session not created")
            return 0
        
        return len(self.websocket.messages)

    def _create_transcription_session(self, model="gpt-4o-transcribe", language="en", noise_reduction="near_field"):
        """Create a transcription session"""
        try:
          config = self._get_session_config(model, language, noise_reduction)
          response = self._openai_client.beta.realtime.transcription_sessions.create(**config)
          return response.client_secret
        except Exception as e:
          self.logger.error(f"Failed to create transcription session: {e}")
          return None

    def _get_session_config(self,model="gpt-4o-transcribe", language="en", noise_reduction="near_field", prompt=""):
        """Get the session configuration for transcription"""
        return {
            "input_audio_format": FORMAT,
            "input_audio_transcription": {
                "model": model,
                "prompt": prompt,
                "language": language
            },
            "turn_detection": None,
            "input_audio_noise_reduction": {
                "type": noise_reduction
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }
    
    async def _connect_websocket(self, client_secret):
        """Connect to OpenAI's Realtime API WebSocket"""
        uri = f"{WEBSOCKET_URI}?intent=transcription&client_secret={client_secret}"
        
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
                "session": self._get_session_config(self.model, self.language, self.noise_reduction, self.instructions)
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
      
    async def ping(self):
        """Ping the OpenAI Realtime API"""
        result = await self.send({
            "type": "transcription_session.update",
            "session": {}
            }, "ping", exception_on_error=False)
        
        if not result:
            self.logger.error("Failed to ping OpenAI Realtime API")
            return False
        
        self.logger.info("Pinged OpenAI Realtime API")
        return True
    
    def get_session_duration(self):
        if self.session_start_time is None:
            return 0
        return asyncio.get_event_loop().time() - self.session_start_time
    
    def get_inactive_duration(self):
        if self.last_activity_time is None:
            return 0
        return asyncio.get_event_loop().time() - self.last_activity_time