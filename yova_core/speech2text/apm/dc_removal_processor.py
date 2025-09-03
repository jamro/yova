"""
DC offset removal processor for modular audio processing pipeline
"""
import numpy as np
from scipy import signal
import logging
from .base_processor import AudioProcessor


class DCRemovalProcessor(AudioProcessor):
    """DC offset removal using high-pass filter and DC blocker"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, cutoff_freq: float = 20.0):
        super().__init__(logger, "DCRemoval", sample_rate=sample_rate, cutoff_freq=cutoff_freq)
        self.sample_rate = sample_rate
        self.cutoff_freq = cutoff_freq
        
        # IIR high-pass filter coefficients/state
        self.hp_b = None
        self.hp_a = None
        self.hp_state = None
        
        # One-pole DC blocker state: y[n] = x[n] - x[n-1] + r*y[n-1]
        self.dc_blocker_r = None
        self.prev_input_sample = 0.0
        self.prev_output_sample = 0.0

    def initialize(self) -> None:
        """Initialize DC removal filters"""
        # Butterworth high-pass to remove very low frequency content
        nyquist = self.sample_rate / 2.0
        normalized_cutoff = max(1e-6, min(self.cutoff_freq / nyquist, 0.99))
        
        # Use first-order for minimal phase distortion
        self.hp_b, self.hp_a = signal.butter(1, normalized_cutoff, btype='high', analog=False)
        self.hp_state = signal.lfilter_zi(self.hp_b, self.hp_a)
        
        # One-pole DC blocker coefficient derived from cutoff
        # Effective cutoff ≈ (1 - r) * fs / (2*pi) → r ≈ 1 - 2*pi*fc/fs
        r = 1.0 - (2.0 * np.pi * float(self.cutoff_freq) / float(self.sample_rate))
        self.dc_blocker_r = float(np.clip(r, 0.90, 0.9999))
        
        # Reset states
        self.prev_input_sample = 0.0
        self.prev_output_sample = 0.0
        
        self.logger.info(
            f"DC removal initialized: cutoff={self.cutoff_freq}Hz, r={self.dc_blocker_r:.5f}"
        )

    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply DC removal using DC blocker followed by high-pass filter"""
        self._ensure_initialized()
        
        if audio_data is None or len(audio_data) == 0:
            return audio_data
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        # DC blocker (in-place, vectorized recurrence)
        x = audio_float
        y = np.empty_like(x)
        r = self.dc_blocker_r
        
        # First sample uses stored state
        y0 = float(x[0]) - self.prev_input_sample + r * self.prev_output_sample
        y[0] = y0
        
        # Remaining samples
        for i in range(1, len(x)):
            y[i] = x[i] - x[i - 1] + r * y[i - 1]
        
        # Update blocker state
        self.prev_input_sample = float(x[-1])
        self.prev_output_sample = float(y[-1])
        
        # Mild high-pass to polish residual offset
        filtered_audio, self.hp_state = signal.lfilter(self.hp_b, self.hp_a, y, zi=self.hp_state)
        
        return self._convert_from_float32(filtered_audio, original_dtype)

    def reset_state(self) -> None:
        """Reset processor state for new audio stream"""
        if self.hp_b is not None and self.hp_a is not None:
            self.hp_state = signal.lfilter_zi(self.hp_b, self.hp_a)
        self.prev_input_sample = 0.0
        self.prev_output_sample = 0.0