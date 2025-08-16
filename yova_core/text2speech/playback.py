from abc import ABC, abstractmethod
from yova_core.core.event_source import EventSource

class Playback(ABC):
    
    @abstractmethod
    async def load(self) -> None:
        """Load the audio"""
        pass
    
    @abstractmethod
    async def play(self) -> None:
        """Play the audio"""
        pass 