"""
Audio normalization processor for modular audio processing pipeline
"""
import numpy as np
import logging
from .base_processor import AudioProcessor


class NormalizationProcessor(AudioProcessor):
    """Audio normalization with RMS targeting and peak limiting"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000,
                 target_rms_dbfs: float = -20.0, peak_limit_dbfs: float = -3.0,
                 ema_alpha: float = 0.1):
        """
        Initialize normalization processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            target_rms_dbfs: Target RMS level in dBFS
            peak_limit_dbfs: Peak limiting level in dBFS
            ema_alpha: EMA smoothing factor for gain control
        """
        super().__init__(logger, "Normalization", 
                        sample_rate=sample_rate, target_rms_dbfs=target_rms_dbfs,
                        peak_limit_dbfs=peak_limit_dbfs, ema_alpha=ema_alpha)
        self.sample_rate = sample_rate
        self.target_rms_dbfs = target_rms_dbfs
        self.peak_limit_dbfs = peak_limit_dbfs
        self.ema_alpha = ema_alpha
        
        # Convert dBFS to linear
        self.target_rms_linear = 10 ** (target_rms_dbfs / 20.0)
        self.peak_limit_linear = 10 ** (peak_limit_dbfs / 20.0)
        
        # Normalization state
        self.norm_gain_ema = 1.0
        
    def initialize(self) -> None:
        """Initialize normalization processor"""
        self.logger.info(f"Normalization initialized: target_rms={self.target_rms_dbfs}dBFS, "
                        f"peak_limit={self.peak_limit_dbfs}dBFS")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply normalization and peak limiting"""
        self._ensure_initialized()
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        # Calculate current RMS
        current_rms = np.sqrt(np.mean(audio_float**2))
        
        if current_rms < 1e-8:
            self.logger.warning("Audio signal too quiet for normalization")
            return audio_data
        
        # Calculate and smooth gain
        instantaneous_gain = self.target_rms_linear / current_rms
        self.norm_gain_ema = ((1.0 - self.ema_alpha) * self.norm_gain_ema + 
                             self.ema_alpha * instantaneous_gain)
        
        # Apply normalization
        normalized_audio = audio_float * self.norm_gain_ema
        
        # Apply peak limiting
        peak_value = np.max(np.abs(normalized_audio))
        if peak_value > self.peak_limit_linear:
            limiting_ratio = self.peak_limit_linear / peak_value
            normalized_audio = normalized_audio * limiting_ratio
            
            if limiting_ratio < 0.8:  # More than 20% reduction
                self.logger.debug(f"Applied peak limiting: {20*np.log10(limiting_ratio):.1f}dB reduction")
        
        return self._convert_from_float32(normalized_audio, original_dtype)
    
    def reset_state(self) -> None:
        """Reset normalization state"""
        self.norm_gain_ema = 1.0
