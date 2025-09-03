from .base_processor import AudioProcessor
from .vad import VAD
import numpy as np


class VADProcessor(AudioProcessor):

    def __init__(self, logger, aggressiveness: int = 1.5, sample_rate: int = 16000, chunk_size: int = 480):
        super().__init__(logger, "VAD", aggressiveness=aggressiveness, sample_rate=sample_rate, chunk_size=chunk_size)
        self.vad = VAD(logger, aggressiveness, sample_rate, chunk_size)

    def process(self, audio_data: np.ndarray) -> np.ndarray:
        # Convert audio data to frame_bytes for VAD processing
        audio_float = self._convert_to_float32(audio_data)
        frame_bytes = (audio_float * 32768.0).astype(np.int16).tobytes()
        
        is_speech = self.vad.is_speech(frame_bytes)
        if is_speech:
            return audio_data
        else:
            return None
    
    def reset_state(self) -> None:
        pass
    
    def initialize(self) -> None:
        pass