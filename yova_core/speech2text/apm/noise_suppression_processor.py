"""
Noise suppression processor for modular audio processing pipeline
"""
import numpy as np
import logging
from .base_processor import AudioProcessor
from .vad import VAD


class NoiseSuppressionProcessor(AudioProcessor):
    """VAD-guided spectral noise suppression"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000, 
                 level: int = 1, frame_duration_ms: int = 10):
        """
        Initialize noise suppression processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            level: Noise suppression level 0-3 (0=off, 1=light, 2=moderate, 3=strong)
            frame_duration_ms: Frame duration for noise suppression in ms
        """
        super().__init__(logger, "NoiseSuppression", 
                        sample_rate=sample_rate, level=level, 
                        frame_duration_ms=frame_duration_ms)
        self.sample_rate = sample_rate
        self.level = level
        self.frame_duration_ms = frame_duration_ms
        
        # Noise suppression parameters
        self.ns_frame_size = None
        self.vad_ns = None
        self.ns_nfft = None
        self.ns_window = None
        self.ns_hop = None
        self.noise_psd = None
        self.ns_strength = 0.0
        self.ns_smoothing = 0.0
        self.prev_gain = None
        
    def initialize(self) -> None:
        """Initialize noise suppression"""
        if self.level <= 0:
            self.logger.info("Noise suppression disabled")
            return
        
        self.ns_frame_size = int(self.sample_rate * self.frame_duration_ms / 1000.0)
        
        # Initialize VAD for noise estimation. Use equivalent chunk size from frame duration.
        vad_chunk_size = int(self.sample_rate * self.frame_duration_ms / 1000.0)
        self.vad_ns = VAD(self.logger, aggressiveness=1, 
                         sample_rate=self.sample_rate, 
                         chunk_size=vad_chunk_size)
        
        # FFT and window setup
        self.ns_nfft = 512 if self.ns_frame_size <= 512 else 1024
        # Use modified Hanning window to avoid zero edges that cause normalization issues
        hanning = np.hanning(self.ns_frame_size)
        # Add small offset to prevent zero edges
        self.ns_window = (hanning + 0.01).astype(np.float32)
        self.ns_hop = max(1, self.ns_frame_size // 4)  # 75% overlap for smoother reconstruction
        
        # Noise suppression strength based on level
        if self.level == 1:
            self.ns_strength = 0.6
            self.ns_smoothing = 0.12
        elif self.level == 2:
            self.ns_strength = 0.85
            self.ns_smoothing = 0.08
        else:  # level >= 3
            self.ns_strength = 1.0
            self.ns_smoothing = 0.05
        
        self.logger.info(f"Noise suppression initialized: level={self.level}, "
                        f"frame_size={self.ns_frame_size} samples")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply noise suppression"""
        self._ensure_initialized()
        
        if self.level <= 0 or self.ns_strength <= 0.0:
            return audio_data
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        # Process in overlapping frames
        num_samples = len(audio_float)
        out = np.zeros(num_samples + self.ns_frame_size, dtype=np.float32)
        win_sum = np.zeros_like(out)
        
        for start in range(0, num_samples, self.ns_hop):
            end = start + self.ns_frame_size
            frame = np.zeros(self.ns_frame_size, dtype=np.float32)
            copy_len = max(0, min(self.ns_frame_size, num_samples - start))
            if copy_len > 0:
                frame[:copy_len] = audio_float[start:start+copy_len]
            
            # VAD on this frame
            vad_slice = frame[:self.ns_frame_size]
            frame_bytes = (vad_slice * 32768.0).astype(np.int16).tobytes()
            is_speech = self.vad_ns.is_speech(frame_bytes)
            
            # STFT processing
            windowed = frame * self.ns_window
            spec = np.fft.rfft(windowed, n=self.ns_nfft)
            power_spec = (np.abs(spec) ** 2).astype(np.float32)
            
            # Update noise PSD
            if self.noise_psd is None:
                self.noise_psd = np.maximum(power_spec * (0.3 if is_speech else 1.0), 1e-10)
            if not is_speech:
                self.noise_psd = ((1.0 - self.ns_smoothing) * self.noise_psd + 
                                self.ns_smoothing * power_spec)
            
            # Wiener gain
            eps = 1e-10
            gain = power_spec / (power_spec + self.ns_strength * self.noise_psd + eps)
            gain = np.clip(gain, 0.15, 1.0)
            
            # Smooth gain transitions to reduce artifacts
            if self.prev_gain is not None:
                gain = 0.7 * gain + 0.3 * self.prev_gain
            self.prev_gain = gain.copy()
            
            enhanced_spec = spec * np.sqrt(gain)
            enhanced_time = np.fft.irfft(enhanced_spec, n=self.ns_nfft)[:self.ns_frame_size]
            
            # Apply window again for proper overlap-add
            enhanced_time *= self.ns_window
            
            # Overlap-add with proper window normalization
            out[start:end] += enhanced_time
            win_sum[start:end] += self.ns_window
        
        # Normalize by window sum to prevent clicking
        nonzero = win_sum > 1e-8
        out[nonzero] /= win_sum[nonzero]
        filtered_audio = out[:num_samples]
        
        return self._convert_from_float32(filtered_audio, original_dtype)
    
    def reset_state(self) -> None:
        """Reset noise suppression state"""
        self.noise_psd = None
        self.prev_gain = None
