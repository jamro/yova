from openai import AsyncOpenAI
import re
import asyncio
from time import sleep
from pydub.playback import _play_with_simpleaudio as play_audio
from yova_shared import get_clean_logger
from yova_core.text2speech.stream_playback import StreamPlayback
from yova_core.text2speech.data_playback import DataPlayback

class SpeechTask:
    def __init__(self, message_id, api_key, logger):
        self.message_id = message_id
        self.logger = get_clean_logger("speech_task", logger)
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=self.api_key)

        self.current_buffer = ""
        self.sentence_endings = ['.', '!', '?', ':', ';']
        self.min_chunk_length = 15
        self.sentence_queue = []
        self.audio_queue = []
        self.audio_task = None
        self.conversion_task = None
        self.current_playback = None
        self.playback_config = {
            "model": "gpt-4o-mini-tts",
            "voice": "coral",
            "speed": 1.25,
            "instructions": "Speak in a friendly, engaging tone. Always answer in Polish."
        }
        self.is_stopped = False
        self.wait_time = 1

    def clean_chunk(self, text_chunk):
         # remove **
        text_chunk = re.sub(r'\*\*', '', text_chunk, flags=re.DOTALL)
        # remove ```
        text_chunk = re.sub(r'```.*?```', '', text_chunk, flags=re.DOTALL)
        # remove #+
        text_chunk = re.sub(r'#+', '', text_chunk)
        return text_chunk

    async def append_chunk(self, text_chunk):
        if self.is_stopped:
            return
        
        self.logger.debug(f"Appending chunk: {text_chunk}")
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
        while len(self.sentence_queue) > 0 and not self.is_stopped:
            self.logger.debug(f"Converting sentence: {self.sentence_queue}")
            text = self.sentence_queue.pop(0)

            try:
                if len(self.audio_queue) == 0 and not self.audio_task:
                    self.logger.debug(f"Creating streaming response")
                    playback = StreamPlayback(self.client, self.logger, text, self.playback_config)
                    await playback.load()
                    self.audio_queue.append(playback)
                else:
                    self.logger.debug(f"Waiting for streaming to finish {1 + 1*len(self.audio_queue)}")
                    await asyncio.sleep(self.wait_time + self.wait_time*len(self.audio_queue))
                    self.logger.debug(f"Creating non-streaming response")
                    playback = DataPlayback(self.client, self.logger, text, self.playback_config)
                    await playback.load()
                    self.audio_queue.append(playback)
                if not self.audio_task:
                    self.logger.debug(f"Creating audio task")
                    self.audio_task = asyncio.create_task(self.play_audio())
                else:
                    self.logger.debug(f"Audio task already exists")
                    
            except Exception as e:
                print(f"Error in speech synthesis: {e}")
                break
        
        self.logger.debug(f"Conversion finished, setting conversion task to None")
        self.conversion_task = None

    async def play_audio(self):
        self.logger.debug(f"Playing audio...")
        while len(self.audio_queue) > 0 and not self.is_stopped:
            self.current_playback = self.audio_queue.pop(0)
            await self.current_playback.play()
            self.current_playback = None
            
            self.logger.debug(f"Playback completed, audio queue: {len(self.audio_queue)}")
        
        self.logger.debug(f"Audio playback finished, setting audio task to None")
        self.audio_task = None


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
            try:
                await self.conversion_task
            except asyncio.CancelledError:
                self.logger.debug("Conversion task was cancelled during completion")
            except Exception as e:
                self.logger.error(f"Error completing conversion task: {e}")
            
        # Wait for any pending audio task to complete
        if self.audio_task:
            try:
                await self.audio_task
            except asyncio.CancelledError:
                self.logger.debug("Audio task was cancelled during completion")
            except Exception as e:
                self.logger.error(f"Error completing audio task: {e}")


    async def stop(self):
        self.logger.info(f"Stopping task: {self.current_buffer}")
        
        # stop immediately
        self.audio_queue = []
        self.sentence_queue = []
        self.is_stopped = True

        if self.current_playback:
            self.logger.info(f"Stopping current playback")
            await self.current_playback.stop()
            self.current_playback = None
        else:
            self.logger.info(f"No current playback to stop")

        if self.conversion_task:
            self.logger.info(f"Stopping conversion task")
            try:
                await self.conversion_task
            except asyncio.CancelledError:
                self.logger.debug("Conversion task was cancelled")
            except Exception as e:
                self.logger.error(f"Error stopping conversion task: {e}")
            self.conversion_task = None
        else:
            self.logger.info(f"No conversion task to stop")

        if self.audio_task:
            self.logger.info(f"Stopping audio task")
            try:
                await self.audio_task
            except asyncio.CancelledError:
                self.logger.debug("Audio task was cancelled")
            except Exception as e:
                self.logger.error(f"Error stopping audio task: {e}")
            self.audio_task = None
        else:
            self.logger.info(f"No audio task to stop")