#!/usr/bin/env python3
"""
ECAPA Audio Preprocessor for Speaker Recognition

This module provides audio preprocessing functionality for ECAPA-TDNN speaker recognition models.
It handles audio loading, resampling, Voice Activity Detection (VAD), mel-frequency feature
extraction, and Cepstral Mean Normalization (CMN).

ECAPA preprocessing pipeline:
1. Audio input: mono, 16 kHz, float32 in [-1, 1] scale
2. Optional start trimming to remove initial silence/noise (default: 200ms)
3. FBank/log-Mel features: n_fft=400, hop_length=160, n_mels=80
4. CMN (Cepstral Mean Normalization)
5. Tensor shape: [1, 80, T] for model input
"""

import numpy as np
import soundfile as sf
from typing import Tuple
import logging

# Set up logging
logger = logging.getLogger(__name__)


class ECAPAPreprocessor:
    """ECAPA audio preprocessing for speaker recognition"""
    
    def __init__(self, 
                 target_sr: int = 16000,
                 n_fft: int = 400,
                 hop_length: int = 160,
                 n_mels: int = 80,
                 fmin: float = 20.0,
                 fmax: float = 7600.0,
                 apply_trim: bool = True,  # Enable start trimming by default (removes first 200ms)
                 trim_start_ms: float = 200.0):
        """
        Initialize ECAPA preprocessor
        
        Args:
            target_sr: Target sample rate (16 kHz recommended)
            n_fft: FFT window size (400 samples ≈ 25ms at 16kHz)
            hop_length: Hop length between frames (160 samples ≈ 10ms at 16kHz)
            n_mels: Number of mel filter banks (80 recommended)
            fmin: Minimum frequency for mel filter banks
            fmax: Maximum frequency for mel filter banks
            apply_trim: Whether to apply start trimming (removes first 200ms)
            trim_start_ms: Duration in milliseconds to remove from start of audio
        """
        self.target_sr = target_sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax
        self.apply_trim = apply_trim
        self.trim_start_ms = trim_start_ms
        
        # Calculate window size in seconds
        self.window_size = n_fft / target_sr
        self.hop_size = hop_length / target_sr
        
        logger.info(f"ECAPA Preprocessor initialized:")
        logger.info(f"  Target SR: {target_sr} Hz")
        logger.info(f"  Window size: {self.window_size:.3f}s")
        logger.info(f"  Hop size: {self.hop_size:.3f}s")
        logger.info(f"  Mel banks: {n_mels} ({fmin:.0f}-{fmax:.0f} Hz)")
        logger.info(f"  Start trimming: {'enabled' if apply_trim else 'disabled'} ({trim_start_ms}ms)")
    
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to target format
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        logger.info(f"Loading audio file: {file_path}")
        
        # Load audio file
        audio, sr = sf.read(file_path)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
            logger.info(f"Converted stereo to mono")
        
        # Resample if necessary
        if sr != self.target_sr:
            logger.info(f"Resampling from {sr} Hz to {self.target_sr} Hz")
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
            logger.warning("Audio values exceed [-1, 1] range, normalizing")
            audio = audio / np.max(np.abs(audio))
        
        logger.info(f"Audio loaded: {len(audio)} samples, {sr} Hz, duration: {len(audio)/sr:.2f}s")
        return audio, sr
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Simple resampling using linear interpolation
        For production use, consider using librosa.resample or scipy.signal.resample
        """
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
    
    def _trim_start(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Remove the first 200ms from the audio to skip initial silence/noise
        
        Args:
            audio: Audio signal
            sr: Sample rate
            
        Returns:
            Audio with first 200ms removed
        """
        if not self.apply_trim:
            return audio
        
        logger.info(f"Trimming first {self.trim_start_ms}ms from audio")
        
        # Calculate samples to remove
        samples_to_remove = int((self.trim_start_ms / 1000.0) * sr)
        
        # Check if audio is long enough to trim
        if len(audio) <= samples_to_remove:
            logger.warning("Audio too short to trim 200ms, returning original")
            return audio
        
        # Remove first 200ms
        trimmed_audio = audio[samples_to_remove:]
        
        logger.info(f"Trimmed: {len(trimmed_audio)/sr:.2f}s (from {len(audio)/sr:.2f}s)")
        
        return trimmed_audio
    
    def extract_mel_features(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract mel-frequency features (FBank)
        
        Args:
            audio: Audio signal
            sr: Sample rate
            
        Returns:
            Mel spectrogram of shape (n_mels, time_frames)
        """
        logger.info("Extracting mel-frequency features")
        
        # Calculate number of frames
        n_frames = 1 + (len(audio) - self.n_fft) // self.hop_length
        
        # Initialize mel spectrogram
        mel_spec = np.zeros((self.n_mels, n_frames))
        
        # Create mel filter bank
        mel_filters = self._create_mel_filterbank(sr)
        
        # Process each frame
        for i in range(n_frames):
            start = i * self.hop_length
            end = start + self.n_fft
            
            if end > len(audio):
                # Pad with zeros if frame extends beyond audio
                frame = np.pad(audio[start:], (0, end - len(audio)), 'constant')
            else:
                frame = audio[start:end]
            
            # Apply Hamming window
            window = np.hamming(self.n_fft)
            frame = frame * window
            
            # FFT
            fft = np.fft.rfft(frame)
            power = np.abs(fft) ** 2
            
            # Apply mel filter bank
            mel_power = np.dot(mel_filters, power)
            
            # Log-mel (avoid log(0))
            mel_spec[:, i] = np.log(np.maximum(mel_power, 1e-10))
        
        logger.info(f"Mel features extracted: {mel_spec.shape}")
        return mel_spec
    
    def _create_mel_filterbank(self, sr: int) -> np.ndarray:
        """
        Create mel filter bank matrix
        
        Args:
            sr: Sample rate
            
        Returns:
            Mel filter bank matrix of shape (n_mels, n_fft//2 + 1)
        """
        # Convert frequencies to mel scale
        def hz_to_mel(f):
            return 2595 * np.log10(1 + f / 700)
        
        def mel_to_hz(m):
            return 700 * (10 ** (m / 2595) - 1)
        
        # Create mel frequency points
        mel_low = hz_to_mel(self.fmin)
        mel_high = hz_to_mel(self.fmax)
        mel_points = np.linspace(mel_low, mel_high, self.n_mels + 2)
        hz_points = mel_to_hz(mel_points)
        
        # Convert to FFT bin indices
        bin_indices = np.round(hz_points * self.n_fft / sr).astype(int)
        bin_indices = np.clip(bin_indices, 0, self.n_fft // 2)
        
        # Create filter bank
        n_bins = self.n_fft // 2 + 1
        filterbank = np.zeros((self.n_mels, n_bins))
        
        for i in range(self.n_mels):
            left = bin_indices[i]
            center = bin_indices[i + 1]
            right = bin_indices[i + 2]
            
            # Triangular filter
            for j in range(left, center):
                filterbank[i, j] = (j - left) / (center - left)
            for j in range(center, right):
                filterbank[i, j] = (right - j) / (right - center)
        
        return filterbank
    
    def apply_cmn(self, mel_spec: np.ndarray) -> np.ndarray:
        """
        Apply Cepstral Mean Normalization (CMN)
        
        Args:
            mel_spec: Mel spectrogram
            
        Returns:
            Normalized mel spectrogram
        """
        logger.info("Applying Cepstral Mean Normalization")
        
        # Calculate mean across time dimension
        mean = np.mean(mel_spec, axis=1, keepdims=True)
        
        # Subtract mean
        normalized = mel_spec - mean
        
        logger.info(f"CMN applied: mean subtracted from each mel channel")
        return normalized
    
    def prepare_model_input(self, mel_spec: np.ndarray) -> np.ndarray:
        """
        Prepare mel spectrogram for model input
        
        Args:
            mel_spec: Mel spectrogram of shape (n_mels, time_frames)
            
        Returns:
            Model input tensor of shape (1, n_mels, time_frames)
        """
        # Add batch dimension and ensure correct shape
        model_input = mel_spec[np.newaxis, :, :]  # Shape: (1, n_mels, time_frames)
        
        # Ensure float32 dtype
        model_input = model_input.astype(np.float32)
        
        logger.info(f"Model input prepared: {model_input.shape}, dtype: {model_input.dtype}")
        return model_input
    
    def process_audio(self, file_path: str) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Complete audio processing pipeline
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (processed_features, model_input, metadata)
        """
        logger.info(f"Processing audio file: {file_path}")
        
        # Load and preprocess audio
        audio, sr = self.load_audio(file_path)
        
        # Apply start trimming if enabled
        if self.apply_trim:
            audio = self._trim_start(audio, sr)
        
        # Extract mel features
        mel_spec = self.extract_mel_features(audio, sr)
        
        # Apply CMN
        mel_spec_normalized = self.apply_cmn(mel_spec)
        
        # Prepare model input
        model_input = self.prepare_model_input(mel_spec_normalized)
        
        # Metadata
        metadata = {
            'file_path': file_path,
            'original_duration': len(audio) / sr,
            'processed_duration': mel_spec.shape[1] * self.hop_length / sr,
            'n_frames': mel_spec.shape[1],
            'n_mels': mel_spec.shape[0],
            'sample_rate': sr,
            'feature_shape': mel_spec.shape,
            'model_input_shape': model_input.shape
        }
        
        logger.info(f"Audio processing completed successfully")
        return mel_spec_normalized, model_input, metadata
