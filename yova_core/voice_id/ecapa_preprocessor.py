#!/usr/bin/env python3
"""
Simplified ECAPA Audio Preprocessor

This module provides basic audio preprocessing functionality for ECAPA-TDNN speaker recognition models.
It handles audio loading, resampling, and basic formatting.
"""

import numpy as np
import soundfile as sf
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ECAPAPreprocessor:
    """Basic audio preprocessing for ECAPA"""
    
    def __init__(self, target_sr: int = 16000, trim_start_ms: float = 200.0):
        """
        Initialize ECAPA preprocessor
        
        Args:
            target_sr: Target sample rate (16 kHz recommended)
            trim_start_ms: Duration in milliseconds to remove from start of audio
        """
        self.target_sr = target_sr
        self.trim_start_ms = trim_start_ms
    
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to target format
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        # Load audio file
        audio, sr = sf.read(file_path)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Resample if necessary
        if sr != self.target_sr:
            audio = self._resample_audio(audio, sr, self.target_sr)
            sr = self.target_sr
        
        # Convert to float32 in [-1, 1] range
        if audio.dtype != np.float32:
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            else:
                audio = audio.astype(np.float32)
        
        # Ensure audio is in [-1, 1] range
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / np.max(np.abs(audio))
        
        # Trim start if requested
        if self.trim_start_ms > 0:
            trim_samples = int(self.trim_start_ms * sr / 1000)
            if len(audio) > trim_samples:
                audio = audio[trim_samples:]
        
        return audio, sr
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple resampling using linear interpolation"""
        if orig_sr == target_sr:
            return audio
        
        # Calculate resampling ratio
        ratio = target_sr / orig_sr
        
        # Calculate new length
        new_length = int(len(audio) * ratio)
        
        # Create new time arrays
        old_time = np.linspace(0, len(audio) - 1, len(audio))
        new_time = np.linspace(0, len(audio) - 1, new_length)
        
        # Linear interpolation
        resampled = np.interp(new_time, old_time, audio)
        
        return resampled
    
    def process_audio(self, file_path: str) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Process audio file for ECAPA model
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (processed_audio, processed_audio, metadata)
        """
        # Load and preprocess audio
        audio, sr = self.load_audio(file_path)
        
        # Basic metadata
        metadata = {
            'file_path': file_path,
            'original_duration': len(audio) / sr,
            'sample_rate': sr,
            'feature_shape': audio.shape,
            'model_input_shape': audio.shape
        }
        
        return audio, audio, metadata
