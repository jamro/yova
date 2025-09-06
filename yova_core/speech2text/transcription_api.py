from abc import ABC, abstractmethod
from typing import Optional


class TranscriptionApi(ABC):
    """Abstract base class for transcription APIs used by the Transcriber class."""
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the transcription API is connected and ready to use."""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the transcription API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the transcription API."""
        pass
    
    @abstractmethod
    async def send_audio_chunk(self, audio_chunk: bytes, exception_on_error: bool = True) -> bool:
        """Send an audio chunk to the transcription API.
        
        Args:
            audio_chunk: Raw audio data to send
            exception_on_error: Whether to raise exception on error
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear_audio_buffer(self, exception_on_error: bool = True) -> bool:
        """Clear the audio buffer in the transcription API.
        
        Args:
            exception_on_error: Whether to raise exception on error
            
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def commit_audio_buffer(self, exception_on_error: bool = True) -> str:
        """Commit the audio buffer and get transcription result.
        
        Args:
            exception_on_error: Whether to raise exception on error
            
        Returns:
            str: The transcribed text, empty string if no transcription
        """
        pass
    
    @abstractmethod
    async def query_error(self) -> Optional[str]:
        """Query for any errors from the transcription API.
        
        Returns:
            Optional[str]: Error message if any, None otherwise
        """
        pass
    
    @abstractmethod
    def get_session_duration(self) -> float:
        """Get the duration of the current session in seconds.
        
        Returns:
            float: Session duration in seconds
        """
        pass
    
    @abstractmethod
    def get_inactive_duration(self) -> float:
        """Get the duration of inactivity in seconds.
        
        Returns:
            float: Inactive duration in seconds
        """
        pass