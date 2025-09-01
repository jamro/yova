#!/usr/bin/env python3
"""
Simplified ECAPA Model for Speaker Recognition

This module contains the ECAPAModel class for extracting speaker embeddings
using the ECAPA-TDNN model from SpeechBrain.
"""

import numpy as np
import torch
import logging
import time

logger = logging.getLogger(__name__)


class ECAPAModel:
    """ECAPA-TDNN model for speaker recognition"""
    
    def __init__(self, model_path: str = None, enable_vad: bool = True, max_seconds: float = 3.0, use_webrtcvad: bool = False, vad_aggressiveness: int = 2, min_seconds_to_vad: float = 2.0, prefer_fast_resample: bool = True, quantize_linear: bool = True):
        """
        Initialize ECAPA model
        
        Args:
            model_path: Path to custom ECAPA model (optional, uses default if None)
            enable_vad: Apply VAD + clipping before embedding
            max_seconds: Target voiced duration to keep before embedding
            use_webrtcvad: Try WebRTC VAD if available, else energy-based fallback (default False for speed)
            vad_aggressiveness: WebRTC VAD aggressiveness (0-3)
            min_seconds_to_vad: Skip VAD entirely for shorter clips (just embed)
            prefer_fast_resample: Use fast linear resampling instead of torchaudio sinc (speed)
            quantize_linear: Apply dynamic int8 quantization to Linear layers on CPU
        """
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Tune PyTorch threading for small conv/linear workloads on Pi
        try:
            torch.set_num_threads(2)
            torch.set_num_interop_threads(1)
        except Exception:
            pass
        self.enable_vad = enable_vad
        self.max_seconds = max_seconds
        self.use_webrtcvad = use_webrtcvad
        self.vad_aggressiveness = max(0, min(3, vad_aggressiveness))
        self.min_seconds_to_vad = max(0.0, float(min_seconds_to_vad))
        self.prefer_fast_resample = bool(prefer_fast_resample)
        self._resamplers = {}
        self.quantize_linear = bool(quantize_linear)
        # Detect if webrtcvad is available at runtime
        self._webrtcvad_available = False
        if self.use_webrtcvad:
            try:
                import webrtcvad  # noqa: F401
                self._webrtcvad_available = True
            except Exception:
                self._webrtcvad_available = False
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
            try:
                self.model.eval()
            except Exception:
                pass
            # Optional dynamic quantization for faster CPU inference
            if self.quantize_linear and self.device.type == "cpu":
                try:
                    torch.backends.quantized.engine = "qnnpack"
                    import torch.nn as nn
                    self.model = torch.quantization.quantize_dynamic(self.model, {nn.Linear}, dtype=torch.qint8)
                    logger.info("ECAPA dynamic quantization (Linear->int8) enabled")
                except Exception as e:
                    logger.debug(f"Dynamic quantization not applied: {e}")
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
            
            # Optional VAD + clipping to reduce compute
            if self.enable_vad and self.max_seconds and self.max_seconds > 0 and (len(audio) / sr) >= self.min_seconds_to_vad:
                original_audio = audio
                original_len = len(original_audio)
                audio = self._apply_vad_and_clip(original_audio, sr, self.max_seconds)
                if len(audio) == 0 and original_len > 0:
                    # Fallback to best-energy clip from original audio
                    audio = self._clip_best_window(original_audio, sr, self.max_seconds)
                logger.debug(f"ECAPA VAD/clipping: {original_len/sr:.2f}s -> {len(audio)/sr:.2f}s")
            # Log length before embedding
            logger.info(f"ECAPA embedding input: {len(audio)} samples, {sr} Hz, {len(audio)/sr:.2f}s")

            # Convert to torch tensor
            t0 = time.perf_counter()
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
            audio_tensor = audio_tensor.to(self.device)
            
            # Extract embedding
            with torch.inference_mode():
                t1 = time.perf_counter()
                embedding = self.model.encode_batch(audio_tensor)
                t2 = time.perf_counter()
                embedding = embedding.squeeze().cpu().numpy()
            t3 = time.perf_counter()
            logger.debug(f"ECAPA stages: to_tensor={(t1-t0)*1000:.1f}ms, encode={(t2-t1)*1000:.1f}ms, to_numpy={(t3-t2)*1000:.1f}ms")
            
            # L2 normalization
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return np.array([])
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio, preferring fast linear interpolation. Falls back to torchaudio if requested."""
        if orig_sr == target_sr:
            return audio
        if self.prefer_fast_resample:
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            if new_length <= 0:
                return audio
            indices = np.linspace(0, len(audio) - 1, new_length, dtype=np.float32)
            return np.interp(indices, np.arange(len(audio), dtype=np.float32), audio.astype(np.float32))
        try:
            import torchaudio
            key = (orig_sr, target_sr)
            if key not in self._resamplers:
                self._resamplers[key] = torchaudio.transforms.Resample(orig_sr, target_sr)
            resampler = self._resamplers[key]
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
            resampled = resampler(audio_tensor)
            return resampled.squeeze().numpy()
        except Exception:
            # Fallback to linear
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            if new_length <= 0:
                return audio
            indices = np.linspace(0, len(audio) - 1, new_length, dtype=np.float32)
            return np.interp(indices, np.arange(len(audio), dtype=np.float32), audio.astype(np.float32))
    
    def _apply_vad_and_clip(self, audio: np.ndarray, sr: int, max_seconds: float) -> np.ndarray:
        """Apply VAD (WebRTC if available, else energy-based) and clip to target duration."""
        target_len = int(sr * max_seconds)
        if len(audio) <= target_len:
            # Still try to remove leading/trailing silence
            voiced = self._trim_silence_energy(audio, sr)
            return voiced
        # Prefer WebRTC VAD if available
        if self._webrtcvad_available:
            try:
                audio_vad = self._vad_webrtc_best_segment(audio, sr, target_len)
                if len(audio_vad) > 0:
                    return audio_vad
            except Exception as e:
                logger.debug(f"WebRTC VAD failed, falling back to energy-based VAD: {e}")
        # Energy-based fallback
        return self._vad_energy_best_window(audio, sr, target_len)
    
    def _float_to_pcm16(self, audio: np.ndarray) -> np.ndarray:
        """Convert float32 [-1,1] to int16."""
        audio_clipped = np.clip(audio, -1.0, 1.0)
        return (audio_clipped * 32767.0).astype(np.int16)
    
    def _vad_webrtc_best_segment(self, audio: np.ndarray, sr: int, target_len: int) -> np.ndarray:
        """Use WebRTC VAD to find the longest voiced segment, then clip to target_len."""
        import webrtcvad
        vad = webrtcvad.Vad(self.vad_aggressiveness)
        frame_ms = 30
        frame_len = int(sr * frame_ms / 1000)
        if frame_len <= 0:
            return audio
        pcm16 = self._float_to_pcm16(audio)
        num_frames = len(pcm16) // frame_len
        if num_frames == 0:
            return audio
        voiced_flags = []
        for i in range(num_frames):
            start = i * frame_len
            end = start + frame_len
            frame_bytes = pcm16[start:end].tobytes()
            try:
                is_voiced = vad.is_speech(frame_bytes, sr)
            except Exception:
                is_voiced = True
            voiced_flags.append(is_voiced)
        # Find longest contiguous voiced region
        best_start = 0
        best_end = 0
        cur_start = None
        for i, flag in enumerate(voiced_flags):
            if flag and cur_start is None:
                cur_start = i
            if (not flag or i == len(voiced_flags) - 1) and cur_start is not None:
                cur_end = i if not flag else i + 1
                if (cur_end - cur_start) > (best_end - best_start):
                    best_start, best_end = cur_start, cur_end
                cur_start = None
        if best_end <= best_start:
            # No voiced region found
            return self._vad_energy_best_window(audio, sr, target_len)
        start_sample = best_start * frame_len
        end_sample = min(len(audio), best_end * frame_len)
        segment = audio[start_sample:end_sample]
        if len(segment) <= target_len:
            return segment
        # Clip to target_len, prefer center of the segment
        start = (len(segment) - target_len) // 2
        return segment[start:start + target_len]
    
    def _vad_energy_best_window(self, audio: np.ndarray, sr: int, target_len: int) -> np.ndarray:
        """Energy-based VAD: choose highest-energy window of length target_len using O(n) cumulative sum."""
        if len(audio) <= target_len:
            return audio
        start = self._best_energy_window_start(audio, target_len)
        start = min(start, len(audio) - target_len)
        return audio[start:start + target_len]
    
    def _clip_best_window(self, audio: np.ndarray, sr: int, max_seconds: float) -> np.ndarray:
        """Clip to max_seconds by selecting the highest-energy window using O(n) cumulative sum."""
        target_len = int(sr * max_seconds)
        if len(audio) <= target_len:
            return audio
        start = self._best_energy_window_start(audio, target_len)
        start = min(start, len(audio) - target_len)
        return audio[start:start + target_len]

    def _best_energy_window_start(self, audio: np.ndarray, target_len: int) -> int:
        """Return start index of highest-energy window of length target_len using cumulative sums."""
        audio_sq = (audio.astype(np.float32) ** 2).astype(np.float32)
        # Prefix sum with leading zero for easy window sums
        cumsum = np.empty(audio_sq.shape[0] + 1, dtype=np.float32)
        cumsum[0] = 0.0
        np.cumsum(audio_sq, dtype=np.float32, out=cumsum[1:])
        # window_sum[i] = sum(audio_sq[i:i+target_len])
        window_sums = cumsum[target_len:] - cumsum[:-target_len]
        if window_sums.shape[0] == 0:
            return 0
        start = int(np.argmax(window_sums))
        return start
    
    def _trim_silence_energy(self, audio: np.ndarray, sr: int, threshold_ratio: float = 0.5) -> np.ndarray:
        """Trim leading/trailing low-energy regions using an energy threshold."""
        win = max(1, int(0.03 * sr))
        energy = np.convolve(audio.astype(np.float32) ** 2, np.ones(win, dtype=np.float32), mode='same')
        threshold = threshold_ratio * np.mean(energy) if len(energy) > 0 else 0
        if threshold <= 0:
            return audio
        voiced = energy > threshold
        if not np.any(voiced):
            return audio
        idx = np.where(voiced)[0]
        start = int(max(0, idx[0] - win))
        end = int(min(len(audio), idx[-1] + win))
        return audio[start:end]
