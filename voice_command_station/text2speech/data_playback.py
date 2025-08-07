from voice_command_station.text2speech.playback import Playback
from voice_command_station.core.logging_utils import get_clean_logger
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio as play_audio
from io import BytesIO
import asyncio

class DataPlayback(Playback):
    def __init__(self, client, logger, text, config={}):
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
        audio = AudioSegment.from_file(BytesIO(self.audio_data), format=self.format)
        self.current_playback = await asyncio.to_thread(play_audio, audio)
        await asyncio.to_thread(self.current_playback.wait_done)

    async def stop(self) -> None:
        self.is_stopped = True
        if self.current_playback:
            self.current_playback.stop()
            self.current_playback = None