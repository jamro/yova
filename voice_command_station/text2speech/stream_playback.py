from voice_command_station.text2speech.playback import Playback
from voice_command_station.core.logging_utils import get_clean_logger
from openai.helpers import LocalAudioPlayer

class StreamPlayback(Playback):
    def __init__(self, client, logger, text, config={}):
        self.client = client
        self.logger = get_clean_logger("stream_playback", logger)
        self.stream_context_manager = None
        self.text = text
        self.stream_audio_player = LocalAudioPlayer()
        self.model = config.get("model", "gpt-4o-mini-tts")
        self.voice = config.get("voice", "coral")
        self.speed = config.get("speed", 1)
        self.instructions = config.get("instructions", "")
        self.format = config.get("format", "pcm")

    async def load(self) -> bool:
        self.stream_context_manager = self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=self.text,
            speed=self.speed,
            response_format=self.format,
            instructions=self.instructions
        )
    
    async def play(self) -> bool:
        self.logger.debug(f"Playing stream for text: {self.text}")
        audio = await self.stream_context_manager.__aenter__()
        await self.stream_audio_player.play(audio)
        await self.stream_context_manager.__aexit__(None, None, None)