#!/usr/bin/env python3

import asyncio
from openai import AsyncOpenAI
from voice_command_station.text2speech.speech_task import SpeechTask

class SpeechHandler:
    def __init__(self, api_key):
        """
        Initialize SpeechHandler for streaming text-to-speech.
        
        Args:
            voice: The voice to use for speech synthesis (coral, alloy, echo, fable, onyx, nova, shimmer)
            min_chunk_length: Minimum characters before processing a chunk
        """
        self.api_key = api_key
        self.tasks = []

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
        task = self.get_task(message_id)
        if task is None:
            task = SpeechTask(message_id, self.api_key)
            self.tasks.append(task)

        await task.append_chunk(text_chunk)

    
    async def process_complete(self, message_id, full_text):
        """
        Process the complete response and speak any remaining text.
        
        Args:
            full_text: The complete response text
        """
        # Speak any remaining text in the buffer

        # remove the task from the list
        task = self.get_task(message_id)
        if task is not None:
            await task.complete()
        self.tasks = [task for task in self.tasks if task.message_id != message_id]
    