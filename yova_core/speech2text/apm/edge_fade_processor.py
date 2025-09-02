"""
Edge fade processor for modular audio processing pipeline
"""
import numpy as np
import logging
from .base_processor import AudioProcessor


class EdgeFadeProcessor(AudioProcessor):
    """Apply edge fading to reduce boundary artifacts"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, 
                 fade_duration_ms: float = 1.0):
        """
        Initialize edge fade processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            fade_duration_ms: Fade duration in milliseconds
        """
        super().__init__(logger, "EdgeFade", 
                        sample_rate=sample_rate, fade_duration_ms=fade_duration_ms)
        self.sample_rate = sample_rate
        self.fade_duration_ms = fade_duration_ms
        self.fade_samples = max(1, int(self.sample_rate * (fade_duration_ms / 1000.0)))
        
    def initialize(self) -> None:
        """Initialize edge fade processor"""
        self.logger.info(f"Edge fade initialized: {self.fade_duration_ms}ms "
                        f"({self.fade_samples} samples)")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply edge fading"""
        self._ensure_initialized()
        
        n = len(audio_data)
        if n <= 2 * self.fade_samples:
            return audio_data
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        # Create fade ramps
        ramp = np.linspace(0.0, 1.0, self.fade_samples, dtype=np.float32)
        
        # Apply fade-in and fade-out
        audio_float[:self.fade_samples] *= ramp
        audio_float[-self.fade_samples:] *= ramp[::-1]
        
        return self._convert_from_float32(audio_float, original_dtype)
    
    def reset_state(self) -> None:
        """Reset edge fade state (no persistent state)"""
        pass
