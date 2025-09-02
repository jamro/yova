"""
Automatic Gain Control (AGC) processor for modular audio processing pipeline
"""
import numpy as np
import logging
from .base_processor import AudioProcessor


class AGCProcessor(AudioProcessor):
    """Automatic Gain Control with dynamic range compression/expansion"""
    
    def __init__(self, logger: logging.Logger, sample_rate: int = 16000,
                 target_level_dbfs: float = -18.0, max_gain_db: float = 20.0,
                 min_gain_db: float = -20.0, attack_time_ms: float = 5.0,
                 release_time_ms: float = 50.0, ratio: float = 4.0,
                 knee_width_db: float = 2.0):
        """
        Initialize AGC processor
        
        Args:
            logger: Logger instance
            sample_rate: Audio sample rate in Hz
            target_level_dbfs: Target output level in dBFS
            max_gain_db: Maximum gain in dB
            min_gain_db: Minimum gain in dB
            attack_time_ms: Attack time in milliseconds
            release_time_ms: Release time in milliseconds
            ratio: Compression ratio (1.0 = no compression, >1.0 = compression)
            knee_width_db: Knee width in dB for soft compression
        """
        super().__init__(logger, "AGC", 
                        sample_rate=sample_rate, target_level_dbfs=target_level_dbfs,
                        max_gain_db=max_gain_db, min_gain_db=min_gain_db,
                        attack_time_ms=attack_time_ms, release_time_ms=release_time_ms,
                        ratio=ratio, knee_width_db=knee_width_db)
        self.sample_rate = sample_rate
        self.target_level_dbfs = target_level_dbfs
        self.max_gain_db = max_gain_db
        self.min_gain_db = min_gain_db
        self.attack_time_ms = attack_time_ms
        self.release_time_ms = release_time_ms
        self.ratio = ratio
        self.knee_width_db = knee_width_db
        
        # Convert parameters to linear and calculate time constants
        self.target_level_linear = 10 ** (target_level_dbfs / 20.0)
        self.max_gain_linear = 10 ** (max_gain_db / 20.0)
        self.min_gain_linear = 10 ** (min_gain_db / 20.0)
        
        # Calculate attack and release coefficients
        self.attack_coeff = np.exp(-1.0 / (attack_time_ms * sample_rate / 1000.0))
        self.release_coeff = np.exp(-1.0 / (release_time_ms * sample_rate / 1000.0))
        
        # AGC state
        self.gain_state = 1.0
        self.envelope_state = 0.0
        
        # Knee parameters
        self.knee_low = 10 ** ((target_level_dbfs - knee_width_db/2) / 20.0)
        self.knee_high = 10 ** ((target_level_dbfs + knee_width_db/2) / 20.0)
        
    def initialize(self) -> None:
        """Initialize AGC processor"""
        self.logger.info(f"AGC initialized: target={self.target_level_dbfs}dBFS, "
                        f"ratio={self.ratio}:1, attack={self.attack_time_ms}ms, "
                        f"release={self.release_time_ms}ms")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply automatic gain control"""
        self._ensure_initialized()
        
        original_dtype = audio_data.dtype
        audio_float = self._convert_to_float32(audio_data)
        
        if len(audio_float) == 0:
            return audio_data
        
        # Calculate envelope using RMS with smoothing
        current_rms = np.sqrt(np.mean(audio_float**2))
        
        # Smooth envelope detection
        if self.envelope_state == 0.0:
            self.envelope_state = current_rms
        else:
            # Use different time constants for attack and release
            if current_rms > self.envelope_state:
                # Attack: fast response to increasing levels (use attack coefficient directly)
                alpha = self.attack_coeff
            else:
                # Release: slower response to decreasing levels (use release coefficient directly)
                alpha = self.release_coeff
            
            self.envelope_state = alpha * self.envelope_state + (1.0 - alpha) * current_rms
        
        # Calculate desired gain based on envelope
        if self.envelope_state > 1e-8:
            desired_gain = self.target_level_linear / self.envelope_state
            
            # Check for invalid gain values
            if not np.isfinite(desired_gain) or desired_gain <= 0:
                self.logger.warning(f"Invalid desired gain: {desired_gain}, using 1.0")
                desired_gain = 1.0
            else:
                # Apply compression ratio
                if self.ratio > 1.0:
                    desired_gain = self._apply_compression_ratio(desired_gain)
                
                # Apply soft knee
                desired_gain = self._apply_soft_knee(desired_gain)
                
                # Limit gain range
                desired_gain = np.clip(desired_gain, self.min_gain_linear, self.max_gain_linear)
        else:
            desired_gain = 1.0
        
        # Smooth gain changes to prevent artifacts
        if self.gain_state == 1.0:
            self.gain_state = desired_gain
        else:
            # Use different time constants for gain changes
            if desired_gain < self.gain_state:
                # Reducing gain: use attack time (fast response)
                alpha = self.attack_coeff
            else:
                # Increasing gain: use release time (slow response)
                alpha = self.release_coeff
            
            self.gain_state = alpha * self.gain_state + (1.0 - alpha) * desired_gain
        
        # Apply gain
        processed_audio = audio_float * self.gain_state
        
        return self._convert_from_float32(processed_audio, original_dtype)
    
    def _apply_compression_ratio(self, gain: float) -> float:
        """Apply compression ratio to gain calculation"""
        # Check for invalid input
        if not np.isfinite(gain) or gain <= 0:
            return 1.0
        
        # Convert gain to dB
        gain_db = 20.0 * np.log10(gain)
        
        # Apply compression ratio
        # If gain_db is positive (signal too quiet), apply full gain
        # If gain_db is negative (signal too loud), apply compression
        if gain_db > 0:
            # Signal is too quiet, apply full gain
            compressed_gain_db = gain_db
        else:
            # Signal is too loud, apply compression
            compressed_gain_db = gain_db / self.ratio
        
        # Convert back to linear
        result = 10 ** (compressed_gain_db / 20.0)
        return result if np.isfinite(result) else 1.0
    
    def _apply_soft_knee(self, gain: float) -> float:
        """Apply soft knee compression"""
        # Check for invalid input
        if not np.isfinite(gain) or gain <= 0:
            return 1.0
        
        # Convert gain to dB
        gain_db = 20.0 * np.log10(gain)
        
        # Apply soft knee around target level
        if gain_db > 0:
            # Signal is too quiet, apply full gain
            return gain
        else:
            # Signal is too loud, apply soft knee compression
            # Calculate knee region based on input level relative to target
            knee_low_db = -self.knee_width_db / 2.0  # Below target
            knee_high_db = self.knee_width_db / 2.0   # Above target
            
            if gain_db > knee_low_db:
                # In knee region, apply gradual compression
                knee_factor = (gain_db - knee_low_db) / (knee_high_db - knee_low_db)
                knee_factor = np.clip(knee_factor, 0.0, 1.0)
                compression_factor = 1.0 + knee_factor * (self.ratio - 1.0)
                compressed_gain_db = gain_db / compression_factor
            else:
                # Above knee, apply full compression
                compressed_gain_db = gain_db / self.ratio
            
            result = 10 ** (compressed_gain_db / 20.0)
            return result if np.isfinite(result) else 1.0
    
    def reset_state(self) -> None:
        """Reset AGC state"""
        self.gain_state = 1.0
        self.envelope_state = 0.0
