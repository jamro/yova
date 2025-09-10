#!/usr/bin/env python3

import asyncio
from openai import AsyncOpenAI
from yova_core.text2speech.speech_task import SpeechTask
from yova_shared import get_clean_logger
from yova_shared import EventEmitter
from typing import Any, Awaitable, Callable
from yova_core.cost_tracker import CostTracker

class SpeechHandler:
    def __init__(self, logger, api_key, playback_config=None, cost_tracker=None):
        """
        Initialize SpeechHandler for streaming text-to-speech.
        
        Args:
            logger: Logger instance
            api_key: OpenAI API key
            playback_config: Optional playback configuration dictionary
        """
        self.logger = get_clean_logger("realtime_transcriber", logger)
        self.api_key = api_key
        self.playback_config = playback_config
        self.tasks = []
        self.is_active = False
        self.ignored_messages = []
        self.event_emitter = EventEmitter(logger=logger)
        self.cost_tracker = cost_tracker or CostTracker(logger)

    def ignore_message(self, message_id):
        if message_id in self.ignored_messages:
            return
        self.ignored_messages.append(message_id)
        self.logger.info(f"Ignoring message: {message_id}")

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
        
    async def process_chunk(self, message_id, text_chunk, priority_score=0):
        """
        Process a text chunk and convert to speech if it forms a complete sentence.
        
        Args:
            message_id: The message id of the chunk
            text_chunk: The text chunk to process
        """
        if not self.is_active or message_id in self.ignored_messages:
            return
        
        task = self.get_task(message_id)
        if task is None:
            task = SpeechTask(message_id, self.api_key, self.logger, self.playback_config, self.cost_tracker)
            task.add_event_listener("playing_audio", self.on_playing_audio)
            self.tasks.append(task)

        await task.append_chunk(text_chunk, priority_score)

    async def on_playing_audio(self, data):
        self.logger.info(f"Playing audio: {data['text'][:100]}...")
        await self.event_emitter.emit_event("playing_audio", {
            "message_id": data["message_id"],
            "text": data["text"]
        })

    async def terminate_all_tasks(self):
        for task in self.tasks:
            self.ignore_message(task.message_id)
            await task.stop()
        self.tasks = []

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
    