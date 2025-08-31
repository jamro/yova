#!/usr/bin/env python3
"""
ECAPA Model for Speaker Recognition

This module contains the ECAPAModel class for extracting speaker embeddings
using the ECAPA-TDNN model from SpeechBrain or fallback implementations.
"""

import os
import numpy as np
import torch
import torchaudio
from typing import Optional
import logging

# Set up logging
logger = logging.getLogger(__name__)


class ECAPAModel:
    """Real ECAPA-TDNN model for speaker recognition"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize ECAPA model
        
        Args:
            model_path: Path to custom ECAPA model (optional, uses default if None)
        """
        self.model = None
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Initializing ECAPA model on device: {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load the ECAPA model"""
        try:
            # Try to use SpeechBrain's pretrained ECAPA model
            from speechbrain.pretrained import EncoderClassifier
            
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"Loading custom ECAPA model from: {self.model_path}")
                self.model = EncoderClassifier.from_hparams(self.model_path)
            else:
                logger.info("Loading SpeechBrain's pretrained ECAPA-TDNN model")
                # Use the default ECAPA-TDNN model
                self.model = EncoderClassifier.from_hparams(
                    "speechbrain/spkrec-ecapa-voxceleb"
                )
            
            # Move model to appropriate device
            self.model = self.model.to(self.device)
            logger.info("ECAPA model loaded successfully")
            
        except ImportError:
            logger.error("SpeechBrain not available. Installing required dependencies...")
            self._install_dependencies()
        except Exception as e:
            logger.error(f"Failed to load ECAPA model: {e}")
            logger.info("Falling back to simplified ECAPA implementation")
            self._load_simplified_model()
    
    def _install_dependencies(self):
        """Install required dependencies"""
        try:
            import subprocess
            import sys
            
            logger.info("Installing SpeechBrain...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "speechbrain"])
            
            # Try loading again
            self._load_model()
            
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            logger.info("Using simplified ECAPA implementation")
            self._load_simplified_model()
    
    def _load_simplified_model(self):
        """Load a simplified ECAPA-like model using torchaudio"""
        try:
            # Use torchaudio's Wav2Vec2 model as a fallback
            logger.info("Loading torchaudio Wav2Vec2 as ECAPA fallback")
            self.model = torchaudio.pipelines.WAV2VEC2_BASE.get_model()
            self.model = self.model.to(self.device)
            logger.info("Fallback model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load fallback model: {e}")
            self.model = None
    
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
            logger.error("No model available for embedding extraction")
            return np.array([])
        
        try:
            # Ensure audio is the right format
            if sr != 16000:
                # Resample to 16kHz if needed
                audio = self._resample_audio(audio, sr, 16000)
                sr = 16000
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)  # Add batch dimension
            audio_tensor = audio_tensor.to(self.device)
            
            # Extract embedding based on model type
            if hasattr(self.model, 'encode_batch'):
                # SpeechBrain ECAPA model
                with torch.no_grad():
                    embedding = self.model.encode_batch(audio_tensor)
                    embedding = embedding.squeeze().cpu().numpy()
            elif hasattr(self.model, 'extract_features'):
                # Wav2Vec2 fallback model
                with torch.no_grad():
                    features = self.model.extract_features(audio_tensor)
                    # Use the last layer features as embedding
                    embedding = features[-1].squeeze().mean(dim=0).cpu().numpy()
            else:
                logger.error("Unknown model type")
                return np.array([])
            
            # L2 normalization
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            logger.info(f"Embedding extracted: {embedding.shape}, norm: {np.linalg.norm(embedding):.6f}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return np.array([])
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio using torchaudio"""
        if orig_sr == target_sr:
            return audio
        
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
        resampler = torchaudio.transforms.Resample(orig_sr, target_sr)
        resampled = resampler(audio_tensor)
        return resampled.squeeze().numpy()
