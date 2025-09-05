"""
Base classes for modular audio processing pipeline
"""
import numpy as np
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from yova_shared import get_clean_logger
import logging


class AudioProcessor(ABC):
    """Base class for all audio processors in the pipeline"""
    
    def __init__(self, logger: logging.Logger, name: str, **kwargs):
        """
        Initialize audio processor
        
        Args:
            logger: Logger instance
            name: Processor name for logging
            **kwargs: Processor-specific configuration
        """
        self.logger = get_clean_logger(name, logger)
        self.name = name
        self.config = kwargs
        self._initialized = False
        
    @abstractmethod
    def initialize(self) -> None:
        """Initialize processor-specific resources (filters, state, etc.)"""
        pass
    
    @abstractmethod
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Process audio data
        
        Args:
            audio_data: Input audio samples (int16 or float32)
            
        Returns:
            Processed audio samples (same format as input)
        """
        pass
    
    @abstractmethod
    def reset_state(self) -> None:
        """Reset processor state for new audio stream"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get processor information and configuration
        
        Returns:
            Dictionary with processor info
        """
        return {
            "name": self.name,
            "initialized": self._initialized,
            "config": self.config
        }
    
    def _ensure_initialized(self) -> None:
        """Ensure processor is initialized before processing"""
        if not self._initialized:
            self.initialize()
            self._initialized = True
    
    def _convert_to_float32(self, audio_data: np.ndarray) -> np.ndarray:
        """Convert audio to float32 for processing"""
        if audio_data.dtype == np.int16:
            return audio_data.astype(np.float32) / 32768.0
        return audio_data.astype(np.float32)
    
    def _convert_from_float32(self, audio_float: np.ndarray, original_dtype: np.dtype) -> np.ndarray:
        """Convert float32 back to original format with smooth scaling to prevent artifacts"""
        if original_dtype == np.int16:
            # Use a more careful conversion to prevent crackling artifacts
            # Scale gradually and use proper rounding
            scaled = audio_float * 32768.0
            
            # Apply soft clipping instead of hard clipping to reduce artifacts
            # This prevents sudden amplitude jumps that cause crackling
            max_val = 32767.0
            min_val = -32768.0
            
            # Soft clipping using tanh-based approach for values near the limits
            clipped = np.where(
                np.abs(scaled) > max_val * 0.95,  # Only apply soft clipping near limits
                np.sign(scaled) * max_val * np.tanh(np.abs(scaled) / max_val),
                scaled
            )
            
            # Ensure we stay within int16 bounds
            clipped = np.clip(clipped, min_val, max_val)
            
            # Use proper rounding instead of truncation
            return np.round(clipped).astype(np.int16)
        return audio_float.astype(original_dtype)


class AudioPipeline:
    """Manages a chain of audio processors"""
    
    def __init__(self, logger: logging.Logger, name: str = "AudioPipeline"):
        """
        Initialize audio pipeline
        
        Args:
            logger: Logger instance
            name: Pipeline name for logging
        """
        self.logger = get_clean_logger(name, logger)
        self.name = name
        self.processors: list[AudioProcessor] = []
        
    def add_processor(self, processor: AudioProcessor) -> 'AudioPipeline':
        """
        Add processor to the pipeline
        
        Args:
            processor: AudioProcessor instance
            
        Returns:
            Self for method chaining
        """
        self.processors.append(processor)
        self.logger.info(f"Added processor '{processor.name}' to pipeline")
        return self
    
    def remove_processor(self, processor_name: str) -> bool:
        """
        Remove processor from pipeline by name
        
        Args:
            processor_name: Name of processor to remove
            
        Returns:
            True if processor was found and removed
        """
        for i, processor in enumerate(self.processors):
            if processor.name == processor_name:
                removed = self.processors.pop(i)
                self.logger.info(f"Removed processor '{removed.name}' from pipeline")
                return True
        self.logger.warning(f"Processor '{processor_name}' not found in pipeline")
        return False
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Process audio through entire pipeline
        
        Args:
            audio_data: Input audio samples
            
        Returns:
            Processed audio samples
        """
        if not self.processors:
            return audio_data
        
        current_audio = audio_data
        for processor in self.processors:
            try:
                current_audio = processor.process(current_audio)
                if current_audio is None:
                    break
            except Exception as e:
                self.logger.error(f"Error in processor '{processor.name}': {e}")
                # stack trace
                traceback.print_exc(limit=10)
                # Continue with previous audio on error
                break
        
        return current_audio
    
    def process_chunk(self, audio_chunk: bytes) -> bytes:
        """
        Process audio chunk (bytes) through pipeline
        
        Args:
            audio_chunk: Raw audio bytes (int16 format)
            
        Returns:
            Processed audio bytes
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Process through pipeline
            processed_array = self.process(audio_array)

            if processed_array is None:
                return None
            
            # Convert back to bytes
            return processed_array.tobytes()
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {e}")
            # stack trace
            traceback.print_exc()
            return audio_chunk
    
    def reset_all_states(self) -> None:
        """Reset state of all processors in pipeline"""
        for processor in self.processors:
            try:
                processor.reset_state()
            except Exception as e:
                self.logger.error(f"Error resetting state for processor '{processor.name}': {e}")
        self.logger.info("Reset all processor states")
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about the pipeline
        
        Returns:
            Dictionary with pipeline information
        """
        return {
            "name": self.name,
            "processor_count": len(self.processors),
            "processors": [processor.get_info() for processor in self.processors]
        }
    
    def __len__(self) -> int:
        """Return number of processors in pipeline"""
        return len(self.processors)
    
    def __iter__(self):
        """Iterate over processors in pipeline"""
        return iter(self.processors)
