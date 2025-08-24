from abc import ABC, abstractmethod
from yova_shared import EventSource

class Playback(EventSource):
    
    @abstractmethod
    async def load(self) -> None:
        """Load the audio"""
        pass
    
    @abstractmethod
    async def play(self) -> None:
        """Play the audio"""
        pass 