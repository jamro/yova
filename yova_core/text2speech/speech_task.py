from openai import AsyncOpenAI
import re
import asyncio
from time import sleep
from pydub.playback import _play_with_simpleaudio as play_audio
from yova_shared import get_clean_logger, EventEmitter
from yova_core.text2speech.stream_playback import StreamPlayback
from yova_core.text2speech.data_playback import DataPlayback
from yova_core.text2speech.base64_playback import Base64Playback

class SpeechTask(EventEmitter):
    def __init__(self, message_id, api_key, logger, playback_config=None):
        super().__init__(logger)
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
        
        # Use provided playback_config or default values
        if playback_config is not None:
            self.playback_config = playback_config
        else:
            self.playback_config = {
                "model": "gpt-4o-mini-tts",
                "voice": "coral",
                "speed": 1.25,
                "instructions": "Speak in a friendly, engaging tone."
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
        
        is_audio_chunk = text_chunk.startswith("data:audio/")
        
        self.logger.debug(f"Appending chunk: {text_chunk[:100]}...")
        if is_audio_chunk:
            # flush current buffer
            if len(self.current_buffer) > 0:
                self.sentence_queue.append(self.current_buffer)
                if not self.conversion_task:
                    self.conversion_task = asyncio.create_task(self.convert_to_speech())
                self.current_buffer = ""

            # add audio chunk to the queue
            self.sentence_queue.append(text_chunk)
            if not self.conversion_task:
                self.conversion_task = asyncio.create_task(self.convert_to_speech())

        else:
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
            text = self.sentence_queue.pop(0)
            self.logger.debug(f"Converting sentence: {text[:100]}...")

            is_audio_chunk = text.startswith("data:audio/")

            try:
                if is_audio_chunk:
                    self.logger.info(f"Creating Base64 audio playback")
                    playback = Base64Playback(self.logger, text)
                    await playback.load()
                    self.audio_queue.append({"playback": playback, "text": text})
                elif len(self.audio_queue) == 0 and not self.current_playback:
                    self.logger.info(f"Creating streaming response")
                    playback = StreamPlayback(self.client, self.logger, text, self.playback_config)
                    await playback.load()
                    self.audio_queue.append({"playback": playback, "text": text})
                else:
                    self.logger.info(f"Waiting for streaming to finish {1 + 1*len(self.audio_queue)}")
                    await asyncio.sleep(self.wait_time + self.wait_time*len(self.audio_queue))
                    self.logger.info(f"Creating non-streaming response")
                    playback = DataPlayback(self.client, self.logger, text, self.playback_config)
                    await playback.load()
                    self.audio_queue.append({"playback": playback, "text": text})
                    
                if not self.audio_task:
                    self.logger.info(f"Creating audio task")
                    self.audio_task = asyncio.create_task(self.play_audio())
                else:
                    self.logger.debug(f"Audio task already exists")
                    
            except Exception as e:
                print(f"Error in speech synthesis: {e}")
                break
        
        self.logger.debug(f"Conversion finished, setting conversion task to None")
        self.conversion_task = None

    async def play_audio(self):
        
        async def on_playback(data):
            self.logger.info(f"Playing audio::: {data}")
            await self.emit_event("playing_audio", {"message_id": self.message_id, "text": data["text"]})

        self.logger.debug(f"Playing audio...")
        while len(self.audio_queue) > 0 and not self.is_stopped:
            item = self.audio_queue.pop(0)
            self.current_playback = item["playback"]
            self.current_playback.add_event_listener("playing_audio", on_playback)
            self.logger.debug(f"Playing audio: {item['text'][:100]}...")
            await self.current_playback.play()
            self.logger.debug(f"Playback completed")
            self.current_playback = None
            
            self.logger.debug(f"Playback completed, audio queue: {len(self.audio_queue)}")
        
        self.logger.debug(f"Audio playback finished, setting audio task to None")
        self.audio_task = None

    async def complete(self):
        self.logger.debug(f"Completing task: {len(self.current_buffer)}")
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