from abc import ABC, abstractmethod
from yova_shared import EventSource
import tiktoken
import math


AUDIO_TOKENS_PER_SECOND = 21

class Playback(EventSource):
    
    @abstractmethod
    async def load(self) -> None:
        """Load the audio"""
        pass
    
    @abstractmethod
    async def play(self) -> None:
        """Play the audio"""
        pass 

    def estimate_tokens(self, text, audio_length_in_seconds):
        # hardcoded cl100k_base emebdding for estimating input text tokens. TTS model is not available and usage of text tokens is marginal anyway.
        input_text_tokens = len(tiktoken.get_encoding("cl100k_base").encode(text))
        output_audio_tokens = math.ceil(audio_length_in_seconds * AUDIO_TOKENS_PER_SECOND)
        return input_text_tokens, output_audio_tokens