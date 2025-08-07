from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
import re
import asyncio
import asyncio
from io import BytesIO
from pydub import AudioSegment
from time import sleep
from pydub.playback import _play_with_simpleaudio as play_audio
from voice_command_station.core.logging_utils import get_clean_logger
import logging

class SpeechTask:
    def __init__(self, message_id, api_key, logger):
        self.message_id = message_id
        self.logger = get_clean_logger("speech_task", logger)
        self.api_key = api_key
        self.voice = 'coral'
        self.speed = 1.25
        self.instructions = "Speak in a friendly, engaging tone. Always answer in Polish."
        self.client = AsyncOpenAI(api_key=self.api_key)

        self.model = "gpt-4o-mini-tts"
        self.stream_audio_player = LocalAudioPlayer()
        self.current_buffer = ""
        self.sentence_endings = ['.', '!', '?', ':', ';']
        self.min_chunk_length = 15
        self.sentence_queue = []
        self.audio_queue = []
        self.audio_task = None
        self.conversion_task = None
        self.is_streaming = False


    def clean_chunk(self, text_chunk):
         # remove **
        text_chunk = re.sub(r'\*\*', '', text_chunk, flags=re.DOTALL)
        # remove ```
        text_chunk = re.sub(r'```.*?```', '', text_chunk, flags=re.DOTALL)
        # remove #+
        text_chunk = re.sub(r'#+', '', text_chunk)
        return text_chunk

    async def append_chunk(self, text_chunk):
        self.logger.info(f"Appending chunk: {text_chunk}")
        text_chunk = self.clean_chunk(text_chunk)

        self.current_buffer += text_chunk
        
        # Check if we have a complete sentence or enough content
        if (len(self.current_buffer) >= self.min_chunk_length and 
            any(self.current_buffer.rstrip().endswith(ending) for ending in self.sentence_endings)):
            
            self.current_buffer = self.current_buffer.strip()
            if self.current_buffer:
                self.sentence_queue.append(self.current_buffer)
                if not self.conversion_task:
                    self.conversion_task = asyncio.create_task(self.convert_to_speech())

            self.current_buffer = ""

    async def convert_to_speech(self):
        self.logger.debug(f"Converting to speech...")
        if len(self.sentence_queue) == 0:
            self.conversion_task = None
            self.logger.debug(f"No sentence queue, setting conversion task to None")
            return

        self.logger.debug(f"Converting sentence: {self.sentence_queue}")
        text = self.sentence_queue.pop(0)

        try:
            if len(self.audio_queue) == 0 and not self.audio_task:
                self.logger.debug(f"Creating streaming response")
                response = self.client.audio.speech.with_streaming_response.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    speed=self.speed,
                    response_format="pcm",
                    instructions=self.instructions
                )
                # store stream to speed up playback
                self.audio_queue.append({
                    "type": "stream",
                    "text": text,
                    "data": response
                })
            else:
                self.logger.debug(f"Waiting for streaming to finish {1 + 1*len(self.audio_queue)}")
                await asyncio.sleep(1 + 1*len(self.audio_queue))
                self.logger.debug(f"Creating non-streaming response")
                response = await self.client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    speed=self.speed,
                    response_format="mp3",
                    instructions=self.instructions
                )
                audio_data = await response.aread()
                self.audio_queue.append({
                    "type": "bytes",
                    "text": text,
                    "data": audio_data
                })
            if not self.audio_task:
                self.logger.debug(f"Creating audio task")
                self.audio_task = asyncio.create_task(self.play_audio())
            else:
                self.logger.debug(f"Audio task already exists")

            await self.convert_to_speech()
                
        except Exception as e:
            print(f"Error in speech synthesis: {e}")
            self.conversion_task = None

    async def play_audio(self):
        self.logger.debug(f"Playing audio...")
        if len(self.audio_queue) == 0:
            self.logger.debug(f"No audio queue, setting audio task to None")
            self.audio_task = None
            return
        
        audio = self.audio_queue.pop(0)
        if audio["type"] == "stream":
            self.logger.debug(f"Playing streaming audio")
            self.is_streaming = True
            response = await audio["data"].__aenter__()
            await self.stream_audio_player.play(response)
            await audio["data"].__aexit__(None, None, None)
            self.is_streaming = False
        elif audio["type"] == "bytes":
            self.logger.debug(f"Playing bytes audio")
            audio = AudioSegment.from_file(BytesIO(audio["data"]), format="mp3")
            playback = await asyncio.to_thread(play_audio, audio)
            await asyncio.to_thread(playback.wait_done)
        
        self.logger.debug(f"Playback completed, audio queue: {len(self.audio_queue)}")

        await self.play_audio()


    async def complete(self):
        self.logger.debug(f"Completing task: {self.current_buffer}")
        self.current_buffer = self.current_buffer.strip()
        if self.current_buffer:
            self.sentence_queue.append(self.current_buffer)
            if not self.conversion_task:
                self.conversion_task = asyncio.create_task(self.convert_to_speech())

        self.current_buffer = ""
        
        # Wait for any pending conversion task to complete
        if self.conversion_task:
            await self.conversion_task
            
        # Wait for any pending audio task to complete
        if self.audio_task:
            await self.audio_task