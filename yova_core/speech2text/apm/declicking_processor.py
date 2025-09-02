"""
Declicking processor for modular audio processing pipeline
"""
import numpy as np
import logging
from .base_processor import AudioProcessor


class DeclickingProcessor(AudioProcessor):
    """Remove single-sample clicks using median/MAD-based outlier detection (optimized)"""
    
    def __init__(self, logger: logging.Logger, window_size: int = 5, 
                 mad_threshold: float = 6.0):
        """
        Initialize declicking processor
        
        Args:
            logger: Logger instance
            window_size: Window size for median calculation (must be odd)
            mad_threshold: MAD threshold multiplier for outlier detection
        """
        super().__init__(logger, "Declicking", 
                        window_size=window_size, mad_threshold=mad_threshold)
        self.window_size = window_size if window_size % 2 == 1 else window_size + 1
        self.mad_threshold = mad_threshold
        self.half = self.window_size // 2
        
    def initialize(self) -> None:
        """Initialize declicking processor"""
        self.logger.info(f"Declicking initialized: window_size={self.window_size}, "
                        f"mad_threshold={self.mad_threshold}")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Remove clicks from audio using optimized vectorized approach"""
        self._ensure_initialized()
        
        if len(audio_data) < 3:
            return audio_data
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        # For small chunks, use simple approach
        if len(audio_float) < 100:
            return self._process_simple(audio_float, original_dtype)
        
        # For larger chunks, use optimized vectorized approach
        return self._process_optimized(audio_float, original_dtype)
    
    def _process_simple(self, audio_float: np.ndarray, original_dtype: np.dtype) -> np.ndarray:
        """Simple processing for small chunks"""
        y = audio_float.copy()
        
        for i in range(self.half, len(audio_float) - self.half):
            # Get window excluding current sample
            window = np.concatenate([audio_float[i-self.half:i], audio_float[i+1:i+1+self.half]])
            med = np.median(window)
            mad = np.median(np.abs(window - med)) + 1e-8
            
            # Replace outlier
            if abs(audio_float[i] - med) > self.mad_threshold * mad:
                y[i] = med
        
        return self._convert_from_float32(y, original_dtype)
    
    def _process_optimized(self, audio_float: np.ndarray, original_dtype: np.dtype) -> np.ndarray:
        """Optimized vectorized processing for larger chunks"""
        y = audio_float.copy()
        
        # Process in chunks to balance memory usage and performance
        chunk_size = 1000
        for start in range(self.half, len(audio_float) - self.half, chunk_size):
            end = min(start + chunk_size, len(audio_float) - self.half)
            
            # Pre-allocate arrays for this chunk
            chunk_len = end - start
            window_size = self.window_size - 1  # Exclude center sample
            windows = np.zeros((chunk_len, window_size), dtype=np.float32)
            
            # Fill windows vectorized
            for i, pos in enumerate(range(start, end)):
                windows[i] = np.concatenate([
                    audio_float[pos-self.half:pos], 
                    audio_float[pos+1:pos+1+self.half]
                ])
            
            # Vectorized median and MAD calculation
            medians = np.median(windows, axis=1)
            mads = np.median(np.abs(windows - medians[:, np.newaxis]), axis=1) + 1e-8
            
            # Vectorized outlier detection and replacement
            center_samples = audio_float[start:end]
            outliers = np.abs(center_samples - medians) > self.mad_threshold * mads
            y[start:end][outliers] = medians[outliers]
        
        return self._convert_from_float32(y, original_dtype)
    
    def reset_state(self) -> None:
        """Reset declicking state (no persistent state)"""
        pass
