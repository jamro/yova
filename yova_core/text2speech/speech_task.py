from openai import AsyncOpenAI
import re
import asyncio
from time import sleep
from pydub.playback import _play_with_simpleaudio as play_audio
from yova_shared import get_clean_logger, EventEmitter
from yova_core.text2speech.stream_playback import StreamPlayback
from yova_core.text2speech.data_playback import DataPlayback
from yova_core.text2speech.base64_playback import Base64Playback
from yova_core.cost_tracker import CostTracker

class SpeechTask(EventEmitter):
    def __init__(self, message_id, api_key, logger, playback_config=None, cost_tracker=None):
        super().__init__(logger)
        self.message_id = message_id
        self.logger = get_clean_logger("speech_task", logger)
        self.logger.setLevel("DEBUG")
        
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=self.api_key)

        self.current_buffer = ""
        self.current_buffer_priority_score = 0
        self.sentence_endings = ['.', '!', '?', ':', ';']
        self.min_chunk_length = 15
        self.sentence_queue = []
        self.audio_queue = []
        self.audio_task = None
        self.conversion_task = None
        self.current_playback = None
        self.cost_tracker = cost_tracker or CostTracker(logger)
        
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
        self.wait_time = 0.2

    def clean_chunk(self, text_chunk):
         # remove **
        text_chunk = re.sub(r'\*\*', '', text_chunk, flags=re.DOTALL)
        # remove ```
        text_chunk = re.sub(r'```.*?```', '', text_chunk, flags=re.DOTALL)
        # remove #+
        text_chunk = re.sub(r'#+', '', text_chunk)
        return text_chunk

    async def append_chunk(self, text_chunk, priority_score=0):
        if self.is_stopped:
            return
        
        is_audio_chunk = text_chunk.startswith("data:audio/")
        
        self.logger.debug(f"Appending chunk: {text_chunk[:100]}...")
        if is_audio_chunk:
            # flush current buffer
            if len(self.current_buffer) > 0:
                self.sentence_queue.append({"text": self.current_buffer, "priority_score": self.current_buffer_priority_score})
                if not self.conversion_task:
                    self.conversion_task = asyncio.create_task(self.convert_to_speech())
                self.current_buffer = ""
                self.current_buffer_priority_score = 0

            # add audio chunk to the queue
            self.sentence_queue.append({"text": text_chunk, "priority_score": priority_score})
            if not self.conversion_task:
                self.conversion_task = asyncio.create_task(self.convert_to_speech())

        else:
            text_chunk = self.clean_chunk(text_chunk)
            self.current_buffer += text_chunk
            self.current_buffer_priority_score = max(self.current_buffer_priority_score, priority_score)
        
            # Check if we have a complete sentence or enough content
            if (len(self.current_buffer) >= self.min_chunk_length and 
                any(self.current_buffer.rstrip().endswith(ending) for ending in self.sentence_endings)):
                
                self.current_buffer = self.current_buffer.strip()
                if self.current_buffer:
                    self.sentence_queue.append({"text": self.current_buffer, "priority_score": self.current_buffer_priority_score})
                    if not self.conversion_task:
                        self.conversion_task = asyncio.create_task(self.convert_to_speech())

                self.current_buffer = ""
                self.current_buffer_priority_score = 0

    async def convert_to_speech(self):
        self.logger.debug(f"Converting to speech...")
        while len(self.sentence_queue) > 0 and not self.is_stopped:
            self.sentence_queue = self.filter_priority_queue(self.sentence_queue)
            sentence_obj = self.sentence_queue.pop(0)
            text = sentence_obj["text"]
            priority_score = sentence_obj["priority_score"]

            self.logger.debug(f"Converting sentence (prio: {priority_score}): {text[:100]}...")

            telemetry = {
                "create_time": asyncio.get_event_loop().time(),
            }

            is_audio_chunk = text.startswith("data:audio/")

            try:
                if is_audio_chunk:
                    self.logger.info(f"Creating Base64 audio playback")
                    playback = Base64Playback(self.logger, text)
                    telemetry["load_start_time"] = asyncio.get_event_loop().time()
                    await playback.load()
                    telemetry["load_end_time"] = asyncio.get_event_loop().time()
                    self.logger.debug(f"Base64 audio playback created")
                    self.audio_queue.append({"playback": playback, "text": text, "telemetry": telemetry, "priority_score": priority_score})
                elif len(self.audio_queue) == 0 and self.current_playback is None:
                    self.logger.info(f"Creating streaming response for text: {text[:100]}...")
                    playback = StreamPlayback(self.client, self.logger, text, self.playback_config, cost_tracker=self.cost_tracker)
                    telemetry["load_start_time"] = asyncio.get_event_loop().time()
                    await playback.load()
                    telemetry["load_end_time"] = asyncio.get_event_loop().time()
                    self.logger.debug(f"Streaming response created")
                    self.audio_queue.append({"playback": playback, "text": text, "telemetry": telemetry, "priority_score": priority_score})
                else:
                    wait_time = self.wait_time*len(self.audio_queue)
                    self.logger.info(f"Waiting for streaming to finish: {wait_time}s")
                    await asyncio.sleep(wait_time)
                    self.logger.info(f"Creating non-streaming response for text: {text[:100]}...")
                    playback = DataPlayback(self.client, self.logger, text, self.playback_config, cost_tracker=self.cost_tracker)
                    telemetry["load_start_time"] = asyncio.get_event_loop().time()
                    await playback.load()
                    telemetry["load_end_time"] = asyncio.get_event_loop().time()
                    self.logger.debug(f"Non-streaming response created")
                    self.audio_queue.append({"playback": playback, "text": text, "telemetry": telemetry, "priority_score": priority_score})
                    
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
            self.logger.info(f"Playing audio: {data['text'][:100]}...")
            await self.emit_event("playing_audio", {"message_id": self.message_id, "text": data["text"]})

        self.logger.debug(f"Playing audio...")
        while len(self.audio_queue) > 0 and not self.is_stopped:
            self.audio_queue = self.filter_priority_queue(self.audio_queue)
            item = self.audio_queue.pop(0)
            item["telemetry"]["pop_time"] = asyncio.get_event_loop().time()
            self.current_playback = item["playback"]
            self.current_playback.add_event_listener("playing_audio", on_playback)
            self.logger.debug(f"Playing audio: {item['text'][:100]}...")
            item["telemetry"]["play_start_time"] = asyncio.get_event_loop().time()
            await self.current_playback.play()
            item["telemetry"]["play_end_time"] = asyncio.get_event_loop().time()
            self.logger.debug(f"Playback completed")
            self.current_playback = None
            
            self.logger.debug(f"Playback completed, audio queue: {len(self.audio_queue)}")
            self.logger.debug(f"Playback Telemetry for {item['text'][:100]}:")
            self.logger.debug(f" - type: {type(item['playback'])}")
            for key, value in item["telemetry"].items():
                self.logger.debug(f" - {key}: {round(1000*(value - item['telemetry']['create_time']))}ms")
        
        self.logger.debug(f"Audio playback finished, setting audio task to None")
        self.audio_task = None

    async def complete(self):
        self.logger.debug(f"Completing task: {len(self.current_buffer)}")
        self.current_buffer = self.current_buffer.strip()
        if self.current_buffer:
            self.sentence_queue.append({"text": self.current_buffer, "priority_score": self.current_buffer_priority_score})
            if not self.conversion_task:
                self.conversion_task = asyncio.create_task(self.convert_to_speech())

        self.current_buffer = ""
        self.current_buffer_priority_score = 0
        
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

    def filter_priority_queue(self, queue):

        self.logger.debug(f"Filtering priority queue: {[[item['priority_score'], item['text'][:100]] for item in queue]}")
      
        if not queue or len(queue) == 0:
            return queue
            
        # Find the highest priority score in the queue
        # Only consider items that have a priority_score key
        items_with_priority = [item for item in queue if 'priority_score' in item]
        if not items_with_priority:
            return queue
            
        max_priority = max(item['priority_score'] for item in items_with_priority)
        
        # Find the first occurrence of the highest priority item
        first_max_priority_index = None
        for i, item in enumerate(queue):
            if item.get('priority_score') == max_priority:
                first_max_priority_index = i
                break
        
        # If we found a highest priority item, return from that index onwards
        if first_max_priority_index is not None:
            return queue[first_max_priority_index:]
        
        # Fallback: return the original queue if no priority scores found
        return queue