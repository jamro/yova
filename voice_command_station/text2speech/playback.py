from abc import ABC, abstractmethod
from voice_command_station.core.event_source import EventSource

class Playback(ABC):
    
    @abstractmethod
    async def load(self) -> bool:
        """Load the audio"""
        pass
    
    @abstractmethod
    async def play(self) -> bool:
        """Play the audio"""
        pass 