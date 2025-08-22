#!/usr/bin/env python3

import logging
import time
from typing import List, Tuple
import numpy as np

class AudioBuffer:
    """
    A class to handle buffering of audio chunks when the transcription session is not ready.
    This allows audio data to be collected and sent later when the session becomes available.
    Audio chunks are automatically filtered out when they become older than the configured threshold.
    """
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, audio_channels: int = 1, 
                 max_age_threshold: float = 30.0):
        """
        Initialize the AudioBuffer.
        
        Args:
            logger: Logger instance for logging operations
            sample_rate: Audio sample rate in Hz (default: 16000)
            audio_channels: Number of audio channels (default: 1)
            max_age_threshold: Maximum age of audio chunks in seconds before they are ignored (default: 30.0)
        """
        self.logger = logger
        self.sample_rate = sample_rate
        self.audio_channels = audio_channels
        self.max_age_threshold = max_age_threshold
        self._audio_chunk_buffer: List[Tuple[float, bytes]] = []
        self._buffered_audio_length: float = 0.0
    
    def add_audio_chunk(self, audio_chunk: bytes) -> None:
        """
        Add an audio chunk to the buffer with current timestamp.
        
        Args:
            audio_chunk: Audio data as bytes
        """
        current_time = time.time()
        self._audio_chunk_buffer.append((current_time, audio_chunk))
        self._buffered_audio_length += self._get_audio_length(audio_chunk)
        self.logger.info(f"Audio chunk buffered at {current_time:.2f}. Total buffered length: {self._buffered_audio_length:.2f}s")
        
        # Clean up old chunks after adding new ones
        self._cleanup_old_chunks()
    
    def get_buffered_chunks(self) -> List[bytes]:
        """
        Get all buffered audio chunks (excluding old ones based on threshold).
        
        Returns:
            List of buffered audio chunks
        """
        self._cleanup_old_chunks()
        return [chunk for _, chunk in self._audio_chunk_buffer]
    
    def get_buffered_chunks_with_timestamps(self) -> List[Tuple[float, bytes]]:
        """
        Get all buffered audio chunks with their timestamps (excluding old ones based on threshold).
        
        Returns:
            List of tuples containing (timestamp, audio_chunk)
        """
        self._cleanup_old_chunks()
        return self._audio_chunk_buffer.copy()
    
    def has_buffered_audio(self) -> bool:
        """
        Check if there are buffered audio chunks waiting to be sent.
        
        Returns:
            True if there are buffered chunks, False otherwise
        """
        self._cleanup_old_chunks()
        return len(self._audio_chunk_buffer) > 0
    
    def get_buffered_audio_info(self) -> dict:
        """
        Get information about buffered audio chunks.
        
        Returns:
            Dictionary containing chunk count, total length, buffer status, and age info
        """
        self._cleanup_old_chunks()
        current_time = time.time()
        chunk_ages = [current_time - timestamp for timestamp, _ in self._audio_chunk_buffer]
        
        return {
            'chunk_count': len(self._audio_chunk_buffer),
            'total_length': self._buffered_audio_length,
            'is_empty': not self.has_buffered_audio(),
            'max_age_threshold': self.max_age_threshold,
            'oldest_chunk_age': max(chunk_ages) if chunk_ages else 0.0,
            'newest_chunk_age': min(chunk_ages) if chunk_ages else 0.0
        }
    
    def clear_buffer(self) -> None:
        """Clear the audio chunk buffer."""
        self._audio_chunk_buffer.clear()
        self._buffered_audio_length = 0.0
        self.logger.info("Audio chunk buffer cleared")
    
    def get_buffer_size(self) -> int:
        """
        Get the number of buffered audio chunks.
        
        Returns:
            Number of buffered chunks
        """
        self._cleanup_old_chunks()
        return len(self._audio_chunk_buffer)
    
    def get_total_buffered_length(self) -> float:
        """
        Get the total length of buffered audio in seconds.
        
        Returns:
            Total buffered audio length in seconds
        """
        self._cleanup_old_chunks()
        return self._buffered_audio_length
    
    def set_max_age_threshold(self, threshold: float) -> None:
        """
        Set the maximum age threshold for audio chunks.
        
        Args:
            threshold: Maximum age in seconds before chunks are ignored
        """
        if threshold < 0:
            raise ValueError("Age threshold must be non-negative")
        
        old_threshold = self.max_age_threshold
        self.max_age_threshold = threshold
        self.logger.info(f"Updated max age threshold from {old_threshold}s to {threshold}s")
        
        # Clean up chunks that may now be too old
        self._cleanup_old_chunks()
    
    def get_max_age_threshold(self) -> float:
        """
        Get the current maximum age threshold.
        
        Returns:
            Current maximum age threshold in seconds
        """
        return self.max_age_threshold
    
    def _cleanup_old_chunks(self) -> None:
        """
        Remove audio chunks that are older than the maximum age threshold.
        This method is called automatically when needed.
        """
        if not self._audio_chunk_buffer:
            return
        
        current_time = time.time()
        initial_count = len(self._audio_chunk_buffer)
        
        # Filter out old chunks and recalculate total length
        new_buffer = []
        new_total_length = 0.0
        
        for timestamp, chunk in self._audio_chunk_buffer:
            age = current_time - timestamp
            if age <= self.max_age_threshold:
                new_buffer.append((timestamp, chunk))
                new_total_length += self._get_audio_length(chunk)
            else:
                self.logger.debug(f"Removing audio chunk older than {self.max_age_threshold}s (age: {age:.2f}s)")
        
        # Update buffer and length
        removed_count = initial_count - len(new_buffer)
        if removed_count > 0:
            self._audio_chunk_buffer = new_buffer
            self._buffered_audio_length = new_total_length
            self.logger.info(f"Removed {removed_count} old audio chunks. Remaining: {len(new_buffer)}")
    
    def _get_audio_length(self, audio_chunk: bytes) -> float:
        """
        Calculate the length of an audio chunk in seconds.
        
        Args:
            audio_chunk: Audio data as bytes
            
        Returns:
            Length of audio chunk in seconds
        """
        if not audio_chunk:
            return 0.0

        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        if len(audio_array) == 0:
            return 0.0

        seconds = len(audio_array) / (self.sample_rate * self.audio_channels)
        return seconds
