"""
Simplified audio processing pipeline - much simpler than the full modular version
"""
import numpy as np
from scipy import signal
import logging
from typing import List, Callable, Optional
from yova_shared import get_clean_logger
from .vad import VAD


class SimpleAudioProcessor:
    """Simplified audio processor - no abstract base class needed"""
    
    def __init__(self, name: str, process_func: Callable[[np.ndarray], np.ndarray], 
                 reset_func: Optional[Callable] = None):
        self.name = name
        self.process_func = process_func
        self.reset_func = reset_func or (lambda: None)
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        return self.process_func(audio_data)
    
    def reset_state(self) -> None:
        self.reset_func()


class SimpleAudioPipeline:
    """Simplified audio pipeline - much simpler than the full version"""
    
    def __init__(self, logger: logging.Logger, name: str = "SimplePipeline"):
        self.logger = get_clean_logger(name, logger)
        self.name = name
        self.processors: List[SimpleAudioProcessor] = []
    
    def add_processor(self, processor: SimpleAudioProcessor) -> 'SimpleAudioPipeline':
        self.processors.append(processor)
        return self
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Process audio through all processors"""
        current_audio = audio_data
        for processor in self.processors:
            current_audio = processor.process(current_audio)
        return current_audio
    
    def process_chunk(self, audio_chunk: bytes) -> bytes:
        """Process audio chunk (bytes) through pipeline"""
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        processed_array = self.process(audio_array)
        return processed_array.tobytes()
    
    def reset_all_states(self) -> None:
        """Reset all processor states"""
        for processor in self.processors:
            processor.reset_state()


def create_simple_speech_pipeline(logger: logging.Logger, sample_rate: int = 16000) -> SimpleAudioPipeline:
    """Create a simple speech processing pipeline with essential steps only"""
    
    # DC removal state
    dc_filter_state = None
    dc_blocker_state = 0.0
    
    def init_dc_filter():
        nonlocal dc_filter_state
        nyquist = sample_rate / 2
        normalized_cutoff = 20.0 / nyquist
        if normalized_cutoff >= 1.0:
            normalized_cutoff = 0.99
        b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        dc_filter_state = signal.lfilter_zi(b, a)
        return b, a
    
    def dc_removal(audio_data: np.ndarray) -> np.ndarray:
        nonlocal dc_filter_state, dc_blocker_state
        
        # Convert to float
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
            is_int16 = True
        else:
            audio_float = audio_data.astype(np.float32)
            is_int16 = False
        
        # Initialize filter if needed
        if dc_filter_state is None:
            b, a = init_dc_filter()
        else:
            # Get filter coefficients (we need to store them)
            nyquist = sample_rate / 2
            normalized_cutoff = 20.0 / nyquist
            if normalized_cutoff >= 1.0:
                normalized_cutoff = 0.99
            b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        
        # Apply DC blocker first
        filtered_audio = np.zeros_like(audio_float)
        for i in range(len(audio_float)):
            if i == 0:
                filtered_audio[i] = audio_float[i] - dc_blocker_state
            else:
                filtered_audio[i] = (audio_float[i] - audio_float[i-1] + 
                                   0.995 * filtered_audio[i-1])
        
        if len(audio_float) > 0:
            dc_blocker_state = audio_float[-1]
        
        # Apply high-pass filter
        filtered_audio, dc_filter_state = signal.lfilter(
            b, a, filtered_audio, zi=dc_filter_state
        )
        
        # Convert back
        if is_int16:
            filtered_audio = np.clip(filtered_audio * 32768.0, -32768, 32767)
            return filtered_audio.astype(np.int16)
        return filtered_audio
    
    def reset_dc_state():
        nonlocal dc_filter_state, dc_blocker_state
        dc_filter_state = None
        dc_blocker_state = 0.0
    
    # Speech high-pass filter state
    speech_filter_state = None
    
    def init_speech_filter():
        nonlocal speech_filter_state
        nyquist = sample_rate / 2
        normalized_cutoff = 70.0 / nyquist
        if normalized_cutoff >= 1.0:
            normalized_cutoff = 0.99
        b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        speech_filter_state = signal.lfilter_zi(b, a)
        return b, a
    
    def speech_highpass(audio_data: np.ndarray) -> np.ndarray:
        nonlocal speech_filter_state
        
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
            is_int16 = True
        else:
            audio_float = audio_data.astype(np.float32)
            is_int16 = False
        
        if speech_filter_state is None:
            b, a = init_speech_filter()
        else:
            nyquist = sample_rate / 2
            normalized_cutoff = 70.0 / nyquist
            if normalized_cutoff >= 1.0:
                normalized_cutoff = 0.99
            b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        
        filtered_audio, speech_filter_state = signal.lfilter(
            b, a, audio_float, zi=speech_filter_state
        )
        
        if is_int16:
            filtered_audio = np.clip(filtered_audio * 32768.0, -32768, 32767)
            return filtered_audio.astype(np.int16)
        return filtered_audio
    
    def reset_speech_filter():
        nonlocal speech_filter_state
        speech_filter_state = None
    
    # Normalization state
    norm_gain_ema = 1.0
    
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        nonlocal norm_gain_ema
        
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
            is_int16 = True
        else:
            audio_float = audio_data.astype(np.float32)
            is_int16 = False
        
        # Calculate RMS and normalize
        current_rms = np.sqrt(np.mean(audio_float**2))
        if current_rms < 1e-8:
            return audio_data
        
        target_rms = 10 ** (-20.0 / 20.0)  # -20 dBFS
        instantaneous_gain = target_rms / current_rms
        norm_gain_ema = 0.9 * norm_gain_ema + 0.1 * instantaneous_gain
        
        normalized_audio = audio_float * norm_gain_ema
        
        # Peak limiting
        peak_value = np.max(np.abs(normalized_audio))
        peak_limit = 10 ** (-3.0 / 20.0)  # -3 dBFS
        if peak_value > peak_limit:
            limiting_ratio = peak_limit / peak_value
            normalized_audio = normalized_audio * limiting_ratio
        
        if is_int16:
            normalized_audio = np.clip(normalized_audio * 32768.0, -32768, 32767)
            return normalized_audio.astype(np.int16)
        return normalized_audio
    
    def reset_normalization():
        nonlocal norm_gain_ema
        norm_gain_ema = 1.0
    
    # Create pipeline
    pipeline = SimpleAudioPipeline(logger, "SimpleSpeechPipeline")
    
    # Add processors
    pipeline.add_processor(SimpleAudioProcessor("DCRemoval", dc_removal, reset_dc_state))
    pipeline.add_processor(SimpleAudioProcessor("SpeechHighPass", speech_highpass, reset_speech_filter))
    pipeline.add_processor(SimpleAudioProcessor("Normalization", normalize_audio, reset_normalization))
    
    return pipeline


def create_minimal_pipeline(logger: logging.Logger, sample_rate: int = 16000) -> SimpleAudioPipeline:
    """Create minimal pipeline with just DC removal and normalization"""
    
    # DC removal state
    dc_filter_state = None
    
    def init_dc_filter():
        nonlocal dc_filter_state
        nyquist = sample_rate / 2
        normalized_cutoff = 20.0 / nyquist
        if normalized_cutoff >= 1.0:
            normalized_cutoff = 0.99
        b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        dc_filter_state = signal.lfilter_zi(b, a)
        return b, a
    
    def dc_removal(audio_data: np.ndarray) -> np.ndarray:
        nonlocal dc_filter_state
        
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
            is_int16 = True
        else:
            audio_float = audio_data.astype(np.float32)
            is_int16 = False
        
        if dc_filter_state is None:
            b, a = init_dc_filter()
        else:
            nyquist = sample_rate / 2
            normalized_cutoff = 20.0 / nyquist
            if normalized_cutoff >= 1.0:
                normalized_cutoff = 0.99
            b, a = signal.butter(2, normalized_cutoff, btype='high', analog=False)
        
        filtered_audio, dc_filter_state = signal.lfilter(
            b, a, audio_float, zi=dc_filter_state
        )
        
        if is_int16:
            filtered_audio = np.clip(filtered_audio * 32768.0, -32768, 32767)
            return filtered_audio.astype(np.int16)
        return filtered_audio
    
    def reset_dc_state():
        nonlocal dc_filter_state
        dc_filter_state = None
    
    # Normalization state
    norm_gain_ema = 1.0
    
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        nonlocal norm_gain_ema
        
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
            is_int16 = True
        else:
            audio_float = audio_data.astype(np.float32)
            is_int16 = False
        
        current_rms = np.sqrt(np.mean(audio_float**2))
        if current_rms < 1e-8:
            return audio_data
        
        target_rms = 10 ** (-20.0 / 20.0)
        instantaneous_gain = target_rms / current_rms
        norm_gain_ema = 0.9 * norm_gain_ema + 0.1 * instantaneous_gain
        
        normalized_audio = audio_float * norm_gain_ema
        
        peak_value = np.max(np.abs(normalized_audio))
        peak_limit = 10 ** (-3.0 / 20.0)
        if peak_value > peak_limit:
            limiting_ratio = peak_limit / peak_value
            normalized_audio = normalized_audio * limiting_ratio
        
        if is_int16:
            normalized_audio = np.clip(normalized_audio * 32768.0, -32768, 32767)
            return normalized_audio.astype(np.int16)
        return normalized_audio
    
    def reset_normalization():
        nonlocal norm_gain_ema
        norm_gain_ema = 1.0
    
    # Create pipeline
    pipeline = SimpleAudioPipeline(logger, "MinimalPipeline")
    pipeline.add_processor(SimpleAudioProcessor("DCRemoval", dc_removal, reset_dc_state))
    pipeline.add_processor(SimpleAudioProcessor("Normalization", normalize_audio, reset_normalization))
    
    return pipeline
