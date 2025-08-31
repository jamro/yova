#!/usr/bin/env python3
"""
Simplified ECAPA Model for Speaker Recognition

This module contains the ECAPAModel class for extracting speaker embeddings
using the ECAPA-TDNN model from SpeechBrain.
"""

import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)


class ECAPAModel:
    """ECAPA-TDNN model for speaker recognition"""
    
    def __init__(self, model_path: str = None):
        """
        Initialize ECAPA model
        
        Args:
            model_path: Path to custom ECAPA model (optional, uses default if None)
        """
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model(model_path)
    
    def _load_model(self, model_path: str):
        """Load the ECAPA model"""
        try:
            from speechbrain.pretrained import EncoderClassifier
            
            if model_path:
                self.model = EncoderClassifier.from_hparams(model_path)
            else:
                self.model = EncoderClassifier.from_hparams(
                    "speechbrain/spkrec-ecapa-voxceleb"
                )
            
            self.model = self.model.to(self.device)
            logger.info("ECAPA model loaded successfully")
            
        except ImportError:
            logger.error("SpeechBrain not available. Please install: pip install speechbrain")
            raise
        except Exception as e:
            logger.error(f"Failed to load ECAPA model: {e}")
            raise
    
    def extract_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract speaker embedding from audio
        
        Args:
            audio: Audio signal (mono, float32, [-1, 1])
            sr: Sample rate
            
        Returns:
            Speaker embedding vector
        """
        if self.model is None:
            return np.array([])
        
        try:
            # Ensure audio is the right format
            if sr != 16000:
                audio = self._resample_audio(audio, sr, 16000)
                sr = 16000
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
            audio_tensor = audio_tensor.to(self.device)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.model.encode_batch(audio_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            # L2 normalization
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return np.array([])
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio using torchaudio"""
        try:
            import torchaudio
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
            resampler = torchaudio.transforms.Resample(orig_sr, target_sr)
            resampled = resampler(audio_tensor)
            return resampled.squeeze().numpy()
        except ImportError:
            # Simple linear interpolation fallback
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio)
