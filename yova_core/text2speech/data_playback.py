from yova_core.text2speech.playback import Playback
from yova_shared import get_clean_logger
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio as play_audio
from io import BytesIO
import asyncio
from yova_shared import EventEmitter
from yova_core.cost_tracker import CostTracker

class DataPlayback(Playback):
    def __init__(self, client, logger, text, config={}, cost_tracker=None):
        super().__init__()
        self.client = client
        self.logger = get_clean_logger("data_playback", logger)
        self.text = text
        self.audio_data = None
        self.model = config.get("model", "gpt-4o-mini-tts")
        self.voice = config.get("voice", "coral")
        self.speed = config.get("speed", 1)
        self.instructions = config.get("instructions", "")
        self.format = config.get("format", "mp3")
        self.current_playback = None
        self.is_stopped = False
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
        response = await self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=self.text,
            speed=self.speed,
            response_format=self.format,
            instructions=self.instructions
        )
        if self.is_stopped:
            return
        self.audio_data = await response.aread()
    
    async def play(self) -> None:
        self.logger.debug(f"Playing data for text: {self.text}")
        await self.event_emitter.emit_event("playing_audio", {"text": self.text})
        audio = AudioSegment.from_file(BytesIO(self.audio_data), format=self.format)
        self.current_playback = await asyncio.to_thread(play_audio, audio)
        t0 = asyncio.get_event_loop().time()
        await asyncio.to_thread(self.current_playback.wait_done)
        duration_in_seconds = asyncio.get_event_loop().time() - t0
        input_text_tokens, output_audio_tokens = self.estimate_tokens(self.instructions + " " + self.text, duration_in_seconds)
        self.cost_tracker.add_model_cost(
            "core",
            model=self.model,
            input_text_tokens=input_text_tokens,
            output_audio_tokens=output_audio_tokens
        )
        self.logger.info(f"Token usage (data playback) - Input: {input_text_tokens}, Output: {output_audio_tokens}")

    async def stop(self) -> None:
        self.is_stopped = True
        if self.current_playback:
            self.current_playback.stop()
            self.current_playback = None