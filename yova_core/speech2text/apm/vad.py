import webrtcvad
from yova_shared import get_clean_logger
import logging
logger = get_clean_logger("vad", logging.getLogger())

class VAD:
    """WebRTC Voice Activity Detection wrapper"""
    
    def __init__(self, logger, aggressiveness: int = 1.5, sample_rate: int = 16000, frame_duration_ms: int = 30):
        """
        Initialize WebRTC VAD
        
        Args:
            aggressiveness: VAD aggressiveness (0-3, where 3 is most aggressive)
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration_ms: Frame duration in milliseconds (10, 20, or 30)
        """
        self.logger = get_clean_logger("vad", logger)
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Validate parameters
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Sample rate {sample_rate} not supported by WebRTC VAD")
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"Frame duration {frame_duration_ms}ms not supported by WebRTC VAD")
        
        self.logger.info(f"WebRTC VAD initialized: aggressiveness={aggressiveness}, "
                   f"sample_rate={sample_rate}Hz, frame_duration={frame_duration_ms}ms")
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Check if audio chunk contains speech
        
        Args:
            audio_chunk: Raw audio bytes (must be exactly frame_size samples)
            
        Returns:
            True if speech is detected, False otherwise
        """
        try:
            # WebRTC VAD expects exactly frame_size samples
            if len(audio_chunk) != self.frame_size * 2:  # 2 bytes per int16 sample
                self.logger.warning(f"Audio chunk size {len(audio_chunk)} doesn't match expected "
                             f"frame size {self.frame_size * 2}")
                return False
            
            return self.vad.is_speech(audio_chunk, self.sample_rate)
        except Exception as e:
            self.logger.error(f"Error in VAD processing: {e}")
            return False
    
    def process_audio_chunk(self, audio_chunk: bytes) -> tuple[bytes, bool]:
        """
        Process audio chunk and return it with speech detection result
        
        Args:
            audio_chunk: Raw audio bytes
            
        Returns:
            Tuple of (audio_chunk, is_speech)
        """
        is_speech = self.is_speech(audio_chunk)
        return audio_chunk, is_speech
