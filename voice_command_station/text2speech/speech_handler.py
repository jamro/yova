#!/usr/bin/env python3

import asyncio
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

class SpeechHandler:
    def __init__(self, api_key, voice="coral", min_chunk_length=15):
        """
        Initialize SpeechHandler for streaming text-to-speech.
        
        Args:
            voice: The voice to use for speech synthesis (coral, alloy, echo, fable, onyx, nova, shimmer)
            min_chunk_length: Minimum characters before processing a chunk
        """
        self.api_key =api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.voice = voice
        self.model = "gpt-4o-mini-tts"
        self.audio_player = LocalAudioPlayer()
        self.current_buffer = ""
        self.sentence_endings = ['.', '!', '?', ':', ';']
        self.min_chunk_length = min_chunk_length
        self.response_format = "pcm"  # Best for low latency
        self.is_speaking = False
        
    async def process_chunk(self, text_chunk):
        """
        Process a text chunk and convert to speech if it forms a complete sentence.
        
        Args:
            text_chunk: The text chunk to process
        """
        self.current_buffer += text_chunk
        
        # Check if we have a complete sentence or enough content
        if (len(self.current_buffer) >= self.min_chunk_length and 
            any(self.current_buffer.rstrip().endswith(ending) for ending in self.sentence_endings)):
            
            await self._speak_text(self.current_buffer.strip())
            self.current_buffer = ""
    
    async def process_complete(self, full_text):
        """
        Process the complete response and speak any remaining text.
        
        Args:
            full_text: The complete response text
        """
        # Speak any remaining text in the buffer
        if self.current_buffer.strip():
            await self._speak_text(self.current_buffer.strip())
            self.current_buffer = ""
    
    async def _speak_text(self, text):
        """
        Convert text to speech and play it.
        
        Args:
            text: The text to convert to speech
        """
        if not text.strip() or self.is_speaking:
            return
            
        self.is_speaking = True
        try:
            async with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format=self.response_format,
                instructions="Speak in a friendly, engaging tone. Always answer in Polish."
            ) as response:
                await self.audio_player.play(response)
        except Exception as e:
            print(f"Error in speech synthesis: {e}")
        finally:
            self.is_speaking = False
    
    def set_voice(self, voice):
        """Change the voice for speech synthesis."""
        self.voice = voice
    
    def clear_buffer(self):
        """Clear the current text buffer."""
        self.current_buffer = "" 