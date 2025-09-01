from yova_shared import get_clean_logger
from yova_core.voice_id.ecapa_model import ECAPAModel 
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
import numpy as np
import time

SAMPLE_RATE = 16000

class VoiceIdManager:
    def __init__(self, logger, users_path, model=None):
        self.logger = get_clean_logger("voice_id_manager", logger)

        self.ecapa_model = model or ECAPAModel(logger)
        self.speaker_verifier = SpeakerVerifier(logger, storage_dir=users_path)


    def enroll_speaker(self, speaker_id: str, pcm16_audio: np.ndarray):
        float32_audio = pcm16_audio.astype(np.float32) / 32767.0
        self.logger.debug(f"Converted to float32: range [{float32_audio.min():.3f}, {float32_audio.max():.3f}]")
        embedding = self.ecapa_model.extract_embedding(float32_audio, SAMPLE_RATE)

        if len(embedding) == 0:
            raise Exception(f"Failed to extract embedding for {speaker_id}")
        
        self.speaker_verifier.enroll_speaker(speaker_id, embedding)
        self.logger.debug(f"Speaker enrolled: {speaker_id}")
        
    def identify_speaker(self, pcm16_audio: np.ndarray):
        t0 = time.perf_counter()
        float32_audio = pcm16_audio.astype(np.float32) / 32767.0
        embedding = self.ecapa_model.extract_embedding(float32_audio, SAMPLE_RATE)

        if len(embedding) == 0:
            raise Exception(f"Failed to extract embedding")

        identified_speaker, similarity, confidence_level, _ = self.speaker_verifier.identify_speaker(embedding)

        self.logger.debug(f"Identified speaker: {identified_speaker} with similarity: {similarity} and confidence level: {confidence_level}")
        t1 = time.perf_counter()
        return {
            "identified_speaker": identified_speaker,
            "similarity": similarity,
            "confidence_level": confidence_level,
            "embedding": embedding,
            "duration": (t1 - t0)*1000
        }