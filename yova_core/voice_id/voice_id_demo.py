#!/usr/bin/env python3
"""
ECAPA Embedding Extraction Script for Biometric People Recognition

This script loads audio files from the tmp directory and extracts ECAPA embeddings
for biometric speaker recognition purposes using the real ECAPA-TDNN model.

ECAPA preprocessing pipeline:
1. Audio input: mono, 16 kHz, float32 in [-1, 1] scale
2. Optional VAD (Voice Activity Detection) to remove long silences/background noise
3. FBank/log-Mel features: n_fft=400, hop_length=160, n_mels=80
4. CMN (Cepstral Mean Normalization)
5. Tensor shape: [1, 80, T] for model input
6. Output: L2-normalized embedding vector from real ECAPA-TDNN model
"""

import os
import glob
import numpy as np
import soundfile as sf
from pathlib import Path
import torch
import torchaudio

from typing import Tuple, List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpeakerVerifier:
    """Speaker verification system using ECAPA embeddings"""
    
    def __init__(self, similarity_threshold: float = 0.2868):  # Optimal threshold from analysis
        """
        Initialize speaker verifier
        
        Args:
            similarity_threshold: Threshold for speaker verification (0.0 to 1.0)
        """
        self.enrolled_speakers: Dict[str, np.ndarray] = {}
        self.similarity_threshold = similarity_threshold
        self.confidence_thresholds = {
            'high': 0.6,      # High confidence threshold
            'medium': 0.4,    # Medium confidence threshold  
            'low': 0.2868     # Low confidence threshold (optimal)
        }
        logger.info(f"Speaker verifier initialized with optimal threshold: {similarity_threshold}")
        logger.info(f"Confidence thresholds: High={self.confidence_thresholds['high']:.4f}, "
                   f"Medium={self.confidence_thresholds['medium']:.4f}, "
                   f"Low={self.confidence_thresholds['low']:.4f}")
    
    def enroll_speaker(self, speaker_id: str, embedding: np.ndarray) -> bool:
        """
        Enroll a new speaker with their embedding
        
        Args:
            speaker_id: Unique identifier for the speaker
            embedding: Speaker's embedding vector
            
        Returns:
            True if enrollment successful, False otherwise
        """
        if speaker_id in self.enrolled_speakers:
            logger.warning(f"Speaker {speaker_id} already enrolled, updating embedding")
        
        # Store original embedding without normalization
        self.enrolled_speakers[speaker_id] = embedding.copy()
        
        logger.info(f"Speaker {speaker_id} enrolled successfully")
        return True
    
    def verify_speaker(self, test_embedding: np.ndarray, speaker_id: str) -> Tuple[bool, float, str, float]:
        """
        Verify if test embedding matches enrolled speaker
        
        Args:
            test_embedding: Test embedding to verify
            speaker_id: ID of the speaker to verify against
            
        Returns:
            Tuple of (is_match, similarity_score, confidence_level, confidence_score)
        """
        if speaker_id not in self.enrolled_speakers:
            logger.warning(f"Speaker {speaker_id} not enrolled")
            return False, 0.0, "none", 0.0
        
        # Validate embeddings
        if len(test_embedding) == 0 or len(self.enrolled_speakers[speaker_id]) == 0:
            logger.error(f"Invalid embedding dimensions: test={len(test_embedding)}, enrolled={len(self.enrolled_speakers[speaker_id])}")
            return False, 0.0, "none", 0.0
        
        # Get enrolled embedding
        enrolled_embedding = self.enrolled_speakers[speaker_id]
        
        # Calculate cosine similarity properly
        test_norm = np.linalg.norm(test_embedding)
        enrolled_norm = np.linalg.norm(enrolled_embedding)
        
        if test_norm == 0 or enrolled_norm == 0:
            logger.error(f"Zero norm embeddings: test={test_norm:.6f}, enrolled={enrolled_norm:.6f}")
            return False, 0.0, "none", 0.0
        
        similarity = np.dot(test_embedding, enrolled_embedding) / (test_norm * enrolled_norm)
        is_match = similarity > self.similarity_threshold
        
        # Calculate confidence level and score
        confidence_level, confidence_score = self._calculate_confidence(similarity)
        
        logger.info(f"Verification {speaker_id}: similarity={similarity:.4f}, match={is_match}, "
                   f"confidence={confidence_level} ({confidence_score:.4f})")
        return is_match, similarity, confidence_level, confidence_score
    
    def _calculate_confidence(self, similarity: float) -> Tuple[str, float]:
        """
        Calculate confidence level and score based on similarity
        
        Args:
            similarity: Cosine similarity score
            
        Returns:
            Tuple of (confidence_level, confidence_score)
        """
        # Normalize similarity to confidence score (0-1)
        # ECAPA scores typically range from -0.1 to 0.8, so we normalize to 0-1
        normalized_similarity = max(0, (similarity + 0.1) / 0.9)
        confidence_score = min(1.0, max(0.0, normalized_similarity))
        
        # Determine confidence level
        if similarity >= self.confidence_thresholds['high']:
            confidence_level = "high"
        elif similarity >= self.confidence_thresholds['medium']:
            confidence_level = "medium"
        elif similarity >= self.confidence_thresholds['low']:
            confidence_level = "low"
        else:
            confidence_level = "none"
        
        return confidence_level, confidence_score
    
    def identify_speaker(self, test_embedding: np.ndarray) -> Tuple[Optional[str], float, str, float]:
        """
        Identify the most likely speaker from enrolled speakers
        
        Args:
            test_embedding: Test embedding to identify
            
        Returns:
            Tuple of (speaker_id, best_similarity, confidence_level, confidence_score) or (None, 0.0, "none", 0.0) if no match
        """
        if not self.enrolled_speakers:
            logger.warning("No speakers enrolled for identification")
            return None, 0.0, "none", 0.0
        
        best_match = None
        best_similarity = -1.0
        
        for speaker_id, enrolled_embedding in self.enrolled_speakers.items():
            # Validate embeddings
            if len(test_embedding) == 0 or len(enrolled_embedding) == 0:
                logger.warning(f"Skipping {speaker_id} due to invalid embedding dimensions")
                continue
            
            # Calculate cosine similarity properly
            test_norm = np.linalg.norm(test_embedding)
            enrolled_norm = np.linalg.norm(enrolled_embedding)
            
            if test_norm == 0 or enrolled_norm == 0:
                logger.warning(f"Skipping {speaker_id} due to zero norm embeddings")
                continue
            
            similarity = np.dot(test_embedding, enrolled_embedding) / (test_norm * enrolled_norm)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = speaker_id
        
        # Check if best match meets threshold
        if best_similarity > self.similarity_threshold:
            confidence_level, confidence_score = self._calculate_confidence(best_similarity)
            logger.info(f"Speaker identified: {best_match} (similarity: {best_similarity:.4f}, "
                       f"confidence: {confidence_level} ({confidence_score:.4f}))")
            return best_match, best_similarity, confidence_level, confidence_score
        else:
            logger.info(f"No speaker match found (best similarity: {best_similarity:.4f})")
            return None, best_similarity, "none", 0.0
    
    def get_enrolled_speakers(self) -> List[str]:
        """Get list of enrolled speaker IDs"""
        return list(self.enrolled_speakers.keys())
    
    def remove_speaker(self, speaker_id: str) -> bool:
        """Remove a speaker from enrollment"""
        if speaker_id in self.enrolled_speakers:
            del self.enrolled_speakers[speaker_id]
            logger.info(f"Speaker {speaker_id} removed from enrollment")
            return True
        return False
    
    def get_confidence_statistics(self, similarities: List[float]) -> Dict[str, Dict[str, float]]:
        """
        Get confidence statistics for a list of similarity scores
        
        Args:
            similarities: List of similarity scores
            
        Returns:
            Dictionary with confidence level statistics
        """
        if not similarities:
            return {}
        
        stats = {}
        for level in ['high', 'medium', 'low']:
            threshold = self.confidence_thresholds[level]
            count = sum(1 for s in similarities if s >= threshold)
            percentage = 100 * count / len(similarities)
            stats[level] = {
                'count': count,
                'total': len(similarities),
                'percentage': percentage,
                'threshold': threshold
            }
        
        return stats

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

class ECAPAPreprocessor:
    """ECAPA audio preprocessing for speaker recognition"""
    
    def __init__(self, 
                 target_sr: int = 16000,
                 n_fft: int = 400,
                 hop_length: int = 160,
                 n_mels: int = 80,
                 fmin: float = 20.0,
                 fmax: float = 7600.0,
                 apply_vad: bool = True,
                 vad_threshold: float = 0.01,
                 min_speech_duration: float = 0.1):
        """
        Initialize ECAPA preprocessor
        
        Args:
            target_sr: Target sample rate (16 kHz recommended)
            n_fft: FFT window size (400 samples ≈ 25ms at 16kHz)
            hop_length: Hop length between frames (160 samples ≈ 10ms at 16kHz)
            n_mels: Number of mel filter banks (80 recommended)
            fmin: Minimum frequency for mel filter banks
            fmax: Maximum frequency for mel filter banks
            apply_vad: Whether to apply Voice Activity Detection
            vad_threshold: Amplitude threshold for VAD
            min_speech_duration: Minimum duration of speech segments to keep
        """
        self.target_sr = target_sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax
        self.apply_vad = apply_vad
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        
        # Calculate window size in seconds
        self.window_size = n_fft / target_sr
        self.hop_size = hop_length / target_sr
        
        logger.info(f"ECAPA Preprocessor initialized:")
        logger.info(f"  Target SR: {target_sr} Hz")
        logger.info(f"  Window size: {self.window_size:.3f}s")
        logger.info(f"  Hop size: {self.hop_size:.3f}s")
        logger.info(f"  Mel banks: {n_mels} ({fmin:.0f}-{fmax:.0f} Hz)")
        logger.info(f"  VAD: {'enabled' if apply_vad else 'disabled'}")
    
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
    
    def _apply_vad(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Simple Voice Activity Detection based on amplitude threshold
        
        Args:
            audio: Audio signal
            sr: Sample rate
            
        Returns:
            Audio with silence removed
        """
        if not self.apply_vad:
            return audio
        
        logger.info("Applying Voice Activity Detection")
        
        # Calculate frame-based energy
        frame_length = int(0.025 * sr)  # 25ms frames
        vad_hop_length = int(0.010 * sr)   # 10ms hop
        
        energy = []
        for i in range(0, len(audio) - frame_length + 1, vad_hop_length):
            frame = audio[i:i + frame_length]
            energy.append(np.mean(frame ** 2))
        
        energy = np.array(energy)
        
        # Find speech segments
        speech_mask = energy > self.vad_threshold
        
        # Apply minimum duration filter
        min_frames = int(self.min_speech_duration * sr / vad_hop_length)
        
        # Find speech boundaries
        speech_segments = []
        start_idx = None
        
        for i, is_speech in enumerate(speech_mask):
            if is_speech and start_idx is None:
                start_idx = i
            elif not is_speech and start_idx is not None:
                if i - start_idx >= min_frames:
                    speech_segments.append((start_idx, i))
                start_idx = None
        
        # Handle case where speech continues to end
        if start_idx is not None and len(speech_mask) - start_idx >= min_frames:
            speech_segments.append((start_idx, len(speech_mask)))
        
        if not speech_segments:
            logger.warning("No speech segments detected, returning original audio")
            return audio
        
        # Extract speech segments
        speech_audio = []
        for start, end in speech_segments:
            start_sample = start * vad_hop_length
            end_sample = min(end * vad_hop_length + frame_length, len(audio))
            speech_audio.append(audio[start_sample:end_sample])
        
        # Concatenate speech segments
        result = np.concatenate(speech_audio)
        
        logger.info(f"VAD: {len(speech_segments)} speech segments, "
                   f"duration: {len(result)/sr:.2f}s (from {len(audio)/sr:.2f}s)")
        
        return result
    
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
        
        # Apply VAD if enabled
        if self.apply_vad:
            audio = self._apply_vad(audio, sr)
        
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


def main():
    """Main function to process audio files from tmp directory"""
    logger.info("Starting ECAPA embedding extraction script")
    logger.info("Note: ECAPA models typically produce similarity scores in these ranges:")
    logger.info("  - Same speaker: 0.5-0.8 (varies with audio quality and conditions)")
    logger.info("  - Different speakers: 0.1-0.4")
    logger.info("  - Optimal threshold: 0.2868 (provides best F1 score)")
    logger.info("  - Confidence levels: High (≥0.6), Medium (≥0.4), Low (≥0.2868)")
    
    # Initialize preprocessor
    preprocessor = ECAPAPreprocessor(
        target_sr=16000,
        n_fft=400,
        hop_length=160,
        n_mels=80,
        fmin=20.0,
        fmax=7600.0,
        apply_vad=True,
        vad_threshold=0.01,
        min_speech_duration=0.1
    )

    # Initialize ECAPA model
    ecapa_model = ECAPAModel(model_path="ecapa_tdnn.h5") # Replace with your custom model path if available

    # Initialize speaker verifier
    speaker_verifier = SpeakerVerifier(similarity_threshold=0.2868)  # Optimal threshold from analysis

    # Find audio files in tmp directory
    tmp_dir = Path("tmp/samples")
    audio_files = list(tmp_dir.glob("*.wav"))
    
    if not audio_files:
        logger.error("No audio files found in tmp directory")
        return
    
    logger.info(f"Found {len(audio_files)} audio files")
    
    # Process each audio file
    results = []
    
    # Process all available audio files
    logger.info(f"Processing all {len(audio_files)} audio files")
    
    for audio_file in audio_files:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {audio_file.name}")
            logger.info(f"{'='*60}")
            
            # Process audio
            mel_spec, model_input, metadata = preprocessor.process_audio(str(audio_file))
            
            # Load raw audio for ECAPA model (ECAPA expects raw audio, not mel spectrogram)
            raw_audio, raw_sr = sf.read(str(audio_file))
            if len(raw_audio.shape) > 1:  # Convert stereo to mono
                raw_audio = np.mean(raw_audio, axis=1)
            
            # Extract embedding using the real ECAPA model
            embedding = ecapa_model.extract_embedding(raw_audio, raw_sr)
            
            # Check if embedding extraction was successful
            if len(embedding) == 0:
                logger.error(f"Failed to extract embedding for {audio_file.name}")
                continue
            
            # Store results
            result = {
                'file_path': str(audio_file),
                'mel_spec': mel_spec,
                'model_input': model_input,
                'embedding': embedding,
                'metadata': metadata,
                'raw_audio': raw_audio,
                'raw_sr': raw_sr
            }
            results.append(result)
            
            # Print summary
            logger.info(f"Processing summary for {audio_file.name}:")
            logger.info(f"  Original duration: {metadata['original_duration']:.2f}s")
            logger.info(f"  Processed duration: {metadata['processed_duration']:.2f}s")
            logger.info(f"  Feature shape: {metadata['feature_shape']}")
            logger.info(f"  Model input shape: {metadata['model_input_shape']}")
            logger.info(f"  Embedding dimension: {len(embedding)}")
            logger.info(f"  Embedding norm: {np.linalg.norm(embedding):.6f}")
            logger.info(f"  Embedding range: [{np.min(embedding):.6f}, {np.max(embedding):.6f}]")
            logger.info(f"  Embedding mean: {np.mean(embedding):.6f}")
            
            # Enroll speaker if it's a new file
            if audio_file.name not in speaker_verifier.get_enrolled_speakers():
                speaker_verifier.enroll_speaker(audio_file.name, embedding)
                logger.info(f"  Speaker enrolled: {audio_file.name}")
            
            # Verify speaker
            is_match, similarity, confidence_level, confidence_score = speaker_verifier.verify_speaker(embedding, audio_file.name)
            
            # Interpretation with confidence
            if is_match:
                logger.info(f"  Interpretation: Speaker verified (similarity: {similarity:.4f}, "
                           f"confidence: {confidence_level} ({confidence_score:.4f}))")
            else:
                logger.info(f"  Interpretation: Speaker not verified (similarity: {similarity:.4f}, "
                           f"confidence: {confidence_level} ({confidence_score:.4f}))")

            
        except Exception as e:
            logger.error(f"Error processing {audio_file}: {e}")
            continue
    
    # Compare embeddings using speaker verification system
    if len(results) >= 2:
        logger.info(f"\n{'='*60}")
        logger.info("Speaker Verification Results")
        logger.info(f"{'='*60}")
        
        # Show enrolled speakers
        enrolled_speakers = speaker_verifier.get_enrolled_speakers()
        logger.info(f"Enrolled speakers: {enrolled_speakers}")
        
        # Test speaker identification for each audio file
        for i, result in enumerate(results):
            test_embedding = result['embedding']
            test_file = Path(result['file_path']).name
            
            logger.info(f"\nTesting speaker identification for: {test_file}")
            
            # Try to identify the speaker
            identified_speaker, similarity, confidence_level, confidence_score = speaker_verifier.identify_speaker(test_embedding)
            
            if identified_speaker:
                logger.info(f"  Identified as: {identified_speaker} (similarity: {similarity:.4f}, "
                           f"confidence: {confidence_level} ({confidence_score:.4f}))")
                
                # Verify against the identified speaker
                is_verified, verify_similarity, verify_confidence_level, verify_confidence_score = speaker_verifier.verify_speaker(test_embedding, identified_speaker)
                logger.info(f"  Verification result: {'PASS' if is_verified else 'FAIL'} "
                           f"(confidence: {verify_confidence_level} ({verify_confidence_score:.4f}))")
                
            else:
                logger.info(f"  No speaker match found (best similarity: {similarity:.4f})")
        
        # Cross-comparison matrix
        logger.info(f"\n{'='*60}")
        logger.info("Cross-Speaker Similarity Matrix")
        logger.info(f"{'='*60}")
        
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                emb1 = results[i]['embedding']
                emb2 = results[j]['embedding']
                
                # Cosine similarity
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                
                file1 = Path(results[i]['file_path']).name
                file2 = Path(results[j]['file_path']).name
                
                logger.info(f"{file1} vs {file2}: {similarity:.4f}")
                
                # Interpretation based on ECAPA model performance (adjusted for typical ECAPA scores)
                if similarity > 0.75:
                    interpretation = "Very similar (likely same speaker)"
                elif similarity > 0.65:
                    interpretation = "Similar (possibly same speaker)"
                elif similarity > 0.55:
                    interpretation = "Moderately similar (could be same speaker)"
                elif similarity > 0.45:
                    interpretation = "Slightly similar (possibly same speaker)"
                elif similarity > 0.35:
                    interpretation = "Weakly similar (unclear)"
                else:
                    interpretation = "Different (likely different speakers)"
                
                logger.info(f"  Interpretation: {interpretation}")
        
        # Enhanced testing: Compare similarity scores based on user IDs
        logger.info(f"\n{'='*60}")
        logger.info("User ID-Based Similarity Analysis")
        logger.info(f"{'='*60}")
        
        # Extract user IDs from filenames (remove last 5 chars: .wav + number)
        user_id_results = []
        for result in results:
            filename = Path(result['file_path']).name
            user_id = filename[:-5]  # Remove last 5 characters (.wav + number)
            user_id_results.append({
                'filename': filename,
                'user_id': user_id,
                'embedding': result['embedding']
            })
        
        # Group by user ID
        user_groups = {}
        for item in user_id_results:
            user_id = item['user_id']
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(item)
        
        logger.info(f"Found {len(user_groups)} unique user IDs:")
        for user_id, files in user_groups.items():
            logger.info(f"  {user_id}: {len(files)} files")
        
        # Test same-user vs different-user similarities
        same_user_similarities = []
        different_user_similarities = []
        
        # Compare all possible combinations
        for i in range(len(user_id_results)):
            for j in range(i + 1, len(user_id_results)):
                item1 = user_id_results[i]
                item2 = user_id_results[j]
                
                # Calculate cosine similarity
                emb1 = item1['embedding']
                emb2 = item2['embedding']
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                
                # Categorize by user ID relationship
                if item1['user_id'] == item2['user_id']:
                    same_user_similarities.append(similarity)
                    logger.info(f"SAME USER: {item1['filename']} vs {item2['filename']}: {similarity:.4f}")
                else:
                    different_user_similarities.append(similarity)
                    logger.info(f"DIFFERENT USER: {item1['filename']} vs {item2['filename']}: {similarity:.4f}")
        
        # Statistical analysis
        if same_user_similarities:
            logger.info(f"\nSame User Statistics:")
            logger.info(f"  Count: {len(same_user_similarities)}")
            logger.info(f"  Mean: {np.mean(same_user_similarities):.4f}")
            logger.info(f"  Std: {np.std(same_user_similarities):.4f}")
            logger.info(f"  Min: {np.min(same_user_similarities):.4f}")
            logger.info(f"  Max: {np.max(same_user_similarities):.4f}")
        
        if different_user_similarities:
            logger.info(f"\nDifferent User Statistics:")
            logger.info(f"  Count: {len(different_user_similarities)}")
            logger.info(f"  Mean: {np.mean(different_user_similarities):.4f}")
            logger.info(f"  Std: {np.std(different_user_similarities):.4f}")
            logger.info(f"  Min: {np.min(different_user_similarities):.4f}")
            logger.info(f"  Max: {np.max(different_user_similarities):.4f}")
        
        # Performance evaluation
        if same_user_similarities and different_user_similarities:
            logger.info(f"\nPerformance Analysis:")
            
            # Calculate optimal threshold
            all_similarities = same_user_similarities + different_user_similarities
            thresholds = np.linspace(min(all_similarities), max(all_similarities), 100)
            
            best_f1 = 0
            best_threshold = 0.5
            best_metrics = {}
            
            for threshold in thresholds:
                # Predictions
                same_user_predictions = [1 if s >= threshold else 0 for s in same_user_similarities]
                different_user_predictions = [0 if s >= threshold else 1 for s in different_user_similarities]
                
                # Calculate metrics
                tp = sum(same_user_predictions)  # True positives (correctly identified same user)
                tn = sum(different_user_predictions)  # True negatives (correctly identified different user)
                fp = len(different_user_predictions) - tn  # False positives
                fn = len(same_user_predictions) - tp  # False negatives
                
                if tp + fp > 0 and tp + fn > 0:
                    precision = tp / (tp + fp)
                    recall = tp / (tp + fn)
                    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                    
                    if f1 > best_f1:
                        best_f1 = f1
                        best_threshold = threshold
                        best_metrics = {
                            'threshold': threshold,
                            'precision': precision,
                            'recall': recall,
                            'f1': f1,
                            'tp': tp,
                            'tn': tn,
                            'fp': fp,
                            'fn': fn
                        }
            
            logger.info(f"  Optimal threshold: {best_threshold:.4f}")
            logger.info(f"  Best F1 score: {best_metrics['f1']:.4f}")
            logger.info(f"  Precision: {best_metrics['precision']:.4f}")
            logger.info(f"  Recall: {best_metrics['recall']:.4f}")
            logger.info(f"  True Positives: {best_metrics['tp']}")
            logger.info(f"  True Negatives: {best_metrics['tn']}")
            logger.info(f"  False Positives: {best_metrics['fp']}")
            logger.info(f"  False Negatives: {best_metrics['fn']}")
            
                    # Current threshold performance
        current_threshold = speaker_verifier.similarity_threshold
        current_tp = sum(1 for s in same_user_similarities if s >= current_threshold)
        current_tn = sum(1 for s in different_user_similarities if s < current_threshold)
        current_fp = len(different_user_similarities) - current_tn
        current_fn = len(same_user_similarities) - current_tp
        
        if current_tp + current_fp > 0 and current_tp + current_fn > 0:
            current_precision = current_tp / (current_tp + current_fp)
            current_recall = current_tp / (current_tp + current_fn)
            current_f1 = 2 * (current_precision * current_recall) / (current_precision + current_recall) if (current_precision + current_recall) > 0 else 0
            
            logger.info(f"\nCurrent Threshold ({current_threshold:.4f}) Performance:")
            logger.info(f"  F1 score: {current_f1:.4f}")
            logger.info(f"  Precision: {current_precision:.4f}")
            logger.info(f"  Recall: {current_recall:.4f}")
            
            # Show confidence distribution for current threshold
            logger.info(f"\nConfidence Distribution Analysis:")
            
            # Get confidence statistics for same and different users
            same_user_stats = speaker_verifier.get_confidence_statistics(same_user_similarities)
            different_user_stats = speaker_verifier.get_confidence_statistics(different_user_similarities)
            
            # Display same user confidence distribution
            logger.info(f"  Same User Confidence Distribution:")
            for level in ['high', 'medium', 'low']:
                if level in same_user_stats:
                    stats = same_user_stats[level]
                    logger.info(f"    {level.capitalize()}: {stats['count']}/{stats['total']} ({stats['percentage']:.1f}%) [≥{stats['threshold']:.4f}]")
            
            # Display different user confidence distribution
            logger.info(f"  Different User Confidence Distribution:")
            for level in ['high', 'medium', 'low']:
                if level in different_user_stats:
                    stats = different_user_stats[level]
                    logger.info(f"    {level.capitalize()}: {stats['count']}/{stats['total']} ({stats['percentage']:.1f}%) [≥{stats['threshold']:.4f}]")
            
            # Calculate confidence-based performance metrics
            logger.info(f"\nConfidence-Based Performance Metrics:")
            for level in ['high', 'medium', 'low']:
                if level in same_user_stats and level in different_user_stats:
                    threshold = speaker_verifier.confidence_thresholds[level]
                    same_count = same_user_stats[level]['count']
                    diff_count = different_user_stats[level]['count']
                    
                    # Calculate precision and recall for this confidence level
                    if same_count + diff_count > 0:
                        precision = same_count / (same_count + diff_count)
                        recall = same_count / len(same_user_similarities) if same_user_similarities else 0
                        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                        
                        logger.info(f"    {level.capitalize()} Confidence (≥{threshold:.4f}): "
                                   f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}")
            
            # Overall confidence summary
            logger.info(f"\nOverall Confidence Summary:")
            total_same = len(same_user_similarities)
            total_diff = len(different_user_similarities)
            
            if total_same > 0 and total_diff > 0:
                # Calculate overall confidence metrics
                high_conf_total = same_user_stats.get('high', {}).get('count', 0) + different_user_stats.get('high', {}).get('count', 0)
                medium_conf_total = same_user_stats.get('medium', {}).get('count', 0) + different_user_stats.get('medium', {}).get('count', 0)
                low_conf_total = same_user_stats.get('low', {}).get('count', 0) + different_user_stats.get('low', {}).get('count', 0)
                
                logger.info(f"  Total samples: {total_same + total_diff}")
                logger.info(f"  High confidence samples: {high_conf_total} ({100*high_conf_total/(total_same + total_diff):.1f}%)")
                logger.info(f"  Medium confidence samples: {medium_conf_total} ({100*medium_conf_total/(total_same + total_diff):.1f}%)")
                logger.info(f"  Low confidence samples: {low_conf_total} ({100*low_conf_total/(total_same + total_diff):.1f}%)")
                
                # Recommendation based on confidence analysis
                logger.info(f"\nRecommendations:")
                if high_conf_total / (total_same + total_diff) > 0.7:
                    logger.info(f"  ✓ High confidence threshold (≥{speaker_verifier.confidence_thresholds['high']:.4f}) provides good separation")
                else:
                    logger.info(f"  ⚠ Consider adjusting high confidence threshold for better separation")
                
                if medium_conf_total / (total_same + total_diff) > 0.5:
                    logger.info(f"  ✓ Medium confidence threshold (≥{speaker_verifier.confidence_thresholds['medium']:.4f}) captures most samples")
                else:
                    logger.info(f"  ⚠ Medium confidence threshold may be too restrictive")
    
    logger.info(f"\n{'='*60}")
    logger.info("ECAPA embedding extraction completed successfully!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
