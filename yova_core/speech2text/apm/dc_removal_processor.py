"""
DC offset removal processor for modular audio processing pipeline
"""
import numpy as np
from scipy import signal
import logging
from .base_processor import AudioProcessor


class DCRemovalProcessor(AudioProcessor):
    """DC offset removal using high-pass filter and DC blocker"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, 
                 cutoff_freq: float = 20.0, dc_blocker_alpha: float = 0.995,
                 method: str = "combined"):
        """
        Initialize DC removal processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            cutoff_freq: High-pass filter cutoff frequency in Hz
            dc_blocker_alpha: DC blocker filter coefficient
            method: DC removal method ("highpass", "blocker", "combined", "smooth", "gentle", "clean", or "chunk_aware")
        """
        super().__init__(logger, "DCRemoval", 
                        sample_rate=sample_rate, cutoff_freq=cutoff_freq,
                        dc_blocker_alpha=dc_blocker_alpha, method=method)
        self.sample_rate = sample_rate
        self.cutoff_freq = cutoff_freq
        self.dc_blocker_alpha = dc_blocker_alpha
        self.method = method
        
        # Filter states
        self.filter_state = None
        self.dc_blocker_state = 0.0
        
    def initialize(self) -> None:
        """Initialize DC removal filters"""
        if self.method in ["highpass", "combined"]:
            self._init_highpass_filter()
        
        # Initialize DC blocker state to 0 for clean start
        self.dc_blocker_state = 0.0
        
        self.logger.info(f"DC removal initialized: method={self.method}, cutoff={self.cutoff_freq}Hz")
        
    def _init_highpass_filter(self):
        """Initialize high-pass Butterworth filter"""
        nyquist = self.sample_rate / 2
        normalized_cutoff = self.cutoff_freq / nyquist
        
        if normalized_cutoff >= 1.0:
            self.logger.warning(f"Cutoff frequency {self.cutoff_freq}Hz too high, using 0.99")
            normalized_cutoff = 0.99
        
        self.b, self.a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        self.filter_state = signal.lfilter_zi(self.b, self.a)
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Process audio to remove DC offset"""
        self._ensure_initialized()
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        if self.method == "highpass":
            processed = self._apply_highpass(audio_float)
        elif self.method == "blocker":
            processed = self._apply_dc_blocker(audio_float)
        elif self.method == "combined":
            step1 = self._apply_dc_blocker(audio_float)
            processed = self._apply_highpass(step1)
        elif self.method == "smooth":
            processed = self._apply_smooth_dc_removal(audio_float)
        elif self.method == "gentle":
            processed = self._apply_gentle_dc_removal(audio_float)
        elif self.method == "clean":
            processed = self._apply_clean_dc_removal(audio_float)
        elif self.method == "chunk_aware":
            processed = self._apply_chunk_aware_dc_removal(audio_float)
        else:
            self.logger.warning(f"Unknown DC removal method: {self.method}")
            processed = audio_float
        
        return self._convert_from_float32(processed, original_dtype)
    
    def _apply_highpass(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply high-pass filter"""
        filtered_audio, self.filter_state = signal.lfilter(
            self.b, self.a, audio_float, zi=self.filter_state
        )
        return filtered_audio
    
    def _apply_dc_blocker(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply DC blocker filter with proper state handling"""
        if len(audio_float) == 0:
            return audio_float
            
        filtered_audio = np.zeros_like(audio_float)
        
        # Apply DC blocker filter: y[n] = x[n] - x[n-1] + alpha * y[n-1]
        # This is a high-pass filter that removes DC offset
        for i in range(len(audio_float)):
            if i == 0:
                # First sample: use previous state for x[n-1]
                filtered_audio[i] = audio_float[i] - self.dc_blocker_state
            else:
                # Standard DC blocker equation
                filtered_audio[i] = (audio_float[i] - audio_float[i-1] + 
                                   self.dc_blocker_alpha * filtered_audio[i-1])
        
        # Update state for next chunk (store last input sample)
        self.dc_blocker_state = audio_float[-1]
        
        return filtered_audio
    
    def _apply_smooth_dc_removal(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply smooth DC removal using median-based DC estimation"""
        if len(audio_float) == 0:
            return audio_float
            
        # Use median instead of mean for more robust DC estimation
        # Median is less sensitive to outliers and transient spikes
        dc_offset = np.median(audio_float)
        
        # Remove DC offset
        dc_removed = audio_float - dc_offset
        
        # No additional smoothing to avoid phase distortion and buzzing
        # The median-based approach is already smooth and artifact-free
        return dc_removed
    
    def _apply_gentle_dc_removal(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply gentle DC removal using a very gentle high-pass filter"""
        if len(audio_float) == 0:
            return audio_float
            
        # Use a very gentle high-pass filter (1st order, very low cutoff)
        # This removes DC without introducing phase distortion or buzzing
        cutoff_freq = 5.0  # Very low cutoff frequency (5 Hz)
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        if normalized_cutoff >= 1.0:
            normalized_cutoff = 0.99
        
        # 1st order Butterworth high-pass filter (gentler than 2nd order)
        from scipy import signal
        b, a = signal.butter(1, normalized_cutoff, btype='high', analog=False)
        
        # Apply filter
        filtered_audio = signal.lfilter(b, a, audio_float)
        
        return filtered_audio
    
    def _apply_clean_dc_removal(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply clean DC removal using adaptive DC estimation without filtering artifacts"""
        if len(audio_float) == 0:
            return audio_float
            
        # Use a robust DC estimation that doesn't introduce artifacts
        # Calculate DC offset using a trimmed mean (remove outliers)
        sorted_audio = np.sort(audio_float)
        trim_percent = 0.1  # Remove 10% of extreme values
        trim_count = int(len(sorted_audio) * trim_percent)
        
        if trim_count > 0:
            # Use trimmed mean for more robust DC estimation
            trimmed_audio = sorted_audio[trim_count:-trim_count]
            dc_offset = np.mean(trimmed_audio)
        else:
            # Fallback to regular mean for very short signals
            dc_offset = np.mean(audio_float)
        
        # Remove DC offset
        dc_removed = audio_float - dc_offset
        
        # Apply very gentle edge smoothing only to prevent clicks at boundaries
        if len(dc_removed) > 10:
            # Only smooth the first and last few samples to prevent boundary clicks
            edge_samples = min(5, len(dc_removed) // 4)
            
            # Gentle fade-in for first few samples
            for i in range(edge_samples):
                fade_factor = (i + 1) / edge_samples
                dc_removed[i] *= fade_factor
            
            # Gentle fade-out for last few samples
            for i in range(edge_samples):
                fade_factor = (edge_samples - i) / edge_samples
                dc_removed[-(i+1)] *= fade_factor
        
        return dc_removed
    
    def _apply_chunk_aware_dc_removal(self, audio_float: np.ndarray) -> np.ndarray:
        """Apply chunk-aware DC removal that minimizes boundary artifacts"""
        if len(audio_float) == 0:
            return audio_float
            
        # Use a very simple approach: just remove the mean without any filtering
        # This avoids any phase distortion or filtering artifacts
        dc_offset = np.mean(audio_float)
        dc_removed = audio_float - dc_offset
        
        # Apply very gentle windowing only at the edges to prevent clicks
        if len(dc_removed) > 20:
            # Apply a very gentle window to the first and last 10 samples
            edge_samples = min(10, len(dc_removed) // 4)
            
            # Create a gentle window function
            window = np.ones(len(dc_removed))
            
            # Apply gentle fade-in to first edge_samples
            for i in range(edge_samples):
                window[i] = (i + 1) / edge_samples
            
            # Apply gentle fade-out to last edge_samples
            for i in range(edge_samples):
                window[-(i+1)] = (i + 1) / edge_samples
            
            # Apply the window
            dc_removed = dc_removed * window
        
        return dc_removed
    
    def reset_state(self) -> None:
        """Reset filter states"""
        if self.method in ["highpass", "combined"]:
            self.filter_state = signal.lfilter_zi(self.b, self.a)
        # Reset DC blocker state to prevent clicks between audio segments
        self.dc_blocker_state = 0.0
