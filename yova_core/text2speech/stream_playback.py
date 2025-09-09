from yova_core.text2speech.playback import Playback
from yova_shared import get_clean_logger, EventEmitter
from openai.helpers import LocalAudioPlayer
import asyncio
from yova_core.cost_tracker import CostTracker
import tiktoken
import math

AUDIO_TOKENS_PER_SECOND = 21

class StreamPlayback(Playback):
    def __init__(self, client, logger, text, config={}, cost_tracker=None):
        super().__init__()
        self.client = client
        self.logger = get_clean_logger("stream_playback", logger)
        self.stream_context_manager = None
        self.text = text
        self.stream_audio_player = LocalAudioPlayer()
        self.model = config.get("model", "gpt-4o-mini-tts")
        self.voice = config.get("voice", "nova")
        self.speed = config.get("speed", 1)
        self.instructions = config.get("instructions", "")
        self.format = config.get("format", "pcm")
        self.is_stopped = False
        self.playback_task = None
        self.event_emitter = EventEmitter(logger=logger)
        self.cost_tracker = cost_tracker or CostTracker(logger)

    def add_event_listener(self, event_type: str, listener):
        """Add an event listener for a specific event type."""
        self.event_emitter.add_event_listener(event_type, listener)

    def remove_event_listener(self, event_type: str, listener):
        """Remove an event listener for a specific event type."""
        self.event_emitter.remove_event_listener(event_type, listener)

    def clear_event_listeners(self, event_type: str = None):
        """Clear all event listeners or listeners for a specific event type."""
        self.event_emitter.clear_event_listeners(event_type)

    async def load(self) -> None:
        self.stream_context_manager = self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=self.text,
            speed=self.speed,
            response_format=self.format,
            instructions=self.instructions
        )
        if self.is_stopped:
            await self.stream_context_manager.__aexit__(None, None, None)
            self.playback_task = None
            return
    
    async def play(self) -> None:
        self.logger.debug(f"Playing stream for text: {self.text}")
        self.is_stopped = False
        
        try:
            audio = await self.stream_context_manager.__aenter__() # audio is AsyncStreamedBinaryAPIResponse
            
            # Create a task for the audio playback so we can cancel it
            self.playback_task = asyncio.create_task(self._play_audio(audio))
            await self.playback_task
            
        except asyncio.CancelledError:
            self.logger.debug("Playback was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error during playback: {e}")
            raise
        finally:
            await self.stream_context_manager.__aexit__(None, None, None)
            self.playback_task = None

    async def _play_audio(self, audio):
        """Internal method to play audio that can be cancelled."""
        if self.is_stopped:
            return
        try:
            # no usage info available for TTS model, need to estimate it
            await self.event_emitter.emit_event("playing_audio", {"text": self.text})
            t0 = asyncio.get_event_loop().time()
            await self.stream_audio_player.play(audio)
            duration_in_seconds = asyncio.get_event_loop().time() - t0
            
            input_text_tokens, output_audio_tokens = self.estimate_tokens(self.instructions + " " + self.text, duration_in_seconds)
            self.cost_tracker.add_model_cost(
                "core",
                model=self.model,
                input_text_tokens=input_text_tokens,
                output_audio_tokens=output_audio_tokens
            )
            self.logger.info(f"Token usage - Input: {input_text_tokens}, Output: {output_audio_tokens}")
        except asyncio.CancelledError:
            self.logger.debug("Audio playback was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in audio playback: {e}")
            raise

    async def stop(self) -> None:
        self.logger.debug("Stopping stream playback")
        self.is_stopped = True
        
        # Cancel the playback task if it exists
        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            self.playback_task = None
        
        # Try to stop the audio player if it has a stop method
        if hasattr(self.stream_audio_player, 'stop'):
            try:
                await self.stream_audio_player.stop()
            except Exception as e:
                self.logger.debug(f"Error stopping audio player: {e}")
        
        # Close the stream context manager if it exists
        if self.stream_context_manager:
            try:
                await self.stream_context_manager.__aexit__(None, None, None)
            except Exception as e:
                self.logger.debug(f"Error closing stream context: {e}")
            self.stream_context_manager = None