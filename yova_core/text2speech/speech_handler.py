#!/usr/bin/env python3

import asyncio
from openai import AsyncOpenAI
from yova_core.text2speech.speech_task import SpeechTask
from yova_shared import get_clean_logger
from yova_shared import EventEmitter
from typing import Any, Awaitable, Callable

class SpeechHandler:
    def __init__(self, logger,api_key):
        """
        Initialize SpeechHandler for streaming text-to-speech.
        
        Args:
            voice: The voice to use for speech synthesis (coral, alloy, echo, fable, onyx, nova, shimmer)
            min_chunk_length: Minimum characters before processing a chunk
        """
        self.logger = get_clean_logger("realtime_transcriber", logger)
        self.api_key = api_key
        self.tasks = []
        self.is_active = False
        self.event_emitter = EventEmitter(logger=logger)

    def add_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        self.event_emitter.add_event_listener(event_type, listener)

    def remove_event_listener(self, event_type: str, listener: Callable[[Any], Awaitable[None]]):
        self.event_emitter.remove_event_listener(event_type, listener)

    def clear_event_listeners(self, event_type: str = None):
        self.event_emitter.clear_event_listeners(event_type)

    def get_task(self, message_id):
        for task in self.tasks:
            if task.message_id == message_id:
                return task
        return None
        
    async def process_chunk(self, message_id, text_chunk):
        """
        Process a text chunk and convert to speech if it forms a complete sentence.
        
        Args:
            message_id: The message id of the chunk
            text_chunk: The text chunk to process
        """
        if not self.is_active:
            return
        
        task = self.get_task(message_id)
        if task is None:
            task = SpeechTask(message_id, self.api_key, self.logger)
            self.tasks.append(task)

        await task.append_chunk(text_chunk)

    
    async def process_complete(self, message_id, full_text):
        """
        Process the complete response and speak any remaining text.
        
        Args:
            full_text: The complete response text
        """
        self.logger.info(f"Processing complete: {full_text}")

        # remove the task from the list
        task = self.get_task(message_id)
        if task is not None:
            await task.complete()

        self.tasks = [task for task in self.tasks if task.message_id != message_id]

        # Emit completion event so listeners know speech playback has finished
        completion_data = {"id": message_id, "text": full_text}
        await self.event_emitter.emit_event("message_completed", completion_data)

    async def start(self):
        """Start the speech handler."""
        self.logger.info("Starting speech handler...")
        self.is_active = True


    async def stop(self):
        """Stop the speech handler."""
        self.logger.info("Stopping speech handler...")
        self.is_active = False
        for task in self.tasks:
            if task:
              await task.stop()
        self.tasks = []
        self.logger.info("Speech handler stopped.")
    