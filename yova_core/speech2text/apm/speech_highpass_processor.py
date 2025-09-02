"""
Speech high-pass filter processor for modular audio processing pipeline
"""
import numpy as np
from scipy import signal
import logging
from .base_processor import AudioProcessor


class SpeechHighPassProcessor(AudioProcessor):
    """Speech high-pass filter to remove rumble (60-80 Hz)"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, 
                 cutoff_freq: float = 70.0):
        """
        Initialize speech high-pass processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            cutoff_freq: Speech high-pass filter cutoff frequency in Hz
        """
        super().__init__(logger, "SpeechHighPass", 
                        sample_rate=sample_rate, cutoff_freq=cutoff_freq)
        self.sample_rate = sample_rate
        self.cutoff_freq = cutoff_freq
        self.filter_state = None
        
    def initialize(self) -> None:
        """Initialize speech high-pass filter"""
        nyquist = self.sample_rate / 2
        normalized_cutoff = self.cutoff_freq / nyquist
        
        if normalized_cutoff >= 1.0:
            self.logger.warning(f"Speech cutoff {self.cutoff_freq}Hz too high, using 0.99")
            normalized_cutoff = 0.99
        
        self.b, self.a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        self.filter_state = signal.lfilter_zi(self.b, self.a)
        self.logger.info(f"Speech high-pass filter initialized: {self.cutoff_freq}Hz cutoff")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply speech high-pass filter"""
        self._ensure_initialized()
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        filtered_audio, self.filter_state = signal.lfilter(
            self.b, self.a, audio_float, zi=self.filter_state
        )
        
        return self._convert_from_float32(filtered_audio, original_dtype)
    
    def reset_state(self) -> None:
        """Reset filter state"""
        self.filter_state = signal.lfilter_zi(self.b, self.a)
