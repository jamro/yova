#!/usr/bin/env python3
"""
Simplified ECAPA Voice ID Demo

This script demonstrates basic voice ID functionality with essential user comparison statistics.
Audio files are read and converted to PCM 16-bit format at the demo level.
"""

import numpy as np
import soundfile as sf
from pathlib import Path
import logging
import time
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
from yova_core.voice_id.ecapa_model import ECAPAModel
from yova_core.voice_id.voice_id_manager import VoiceIdManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_audio_as_pcm16(file_path: str) -> tuple[np.ndarray, int]:
    try:
        # Load audio file
        audio, sr = sf.read(file_path)
        
        # Convert to mono if stereo (assume all files are mono as per user request)
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Resample to 16kHz if necessary (assume all files are 16kHz as per user request)
        if sr != 16000:
            # Simple linear interpolation resampling
            ratio = 16000 / sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            audio = np.interp(indices, np.arange(len(audio)), audio)
            sr = 16000
        
        # Convert to PCM 16-bit format (int16) - same as transcriber
        if audio.dtype != np.int16:
            # Convert from float32 [-1, 1] to int16 [-32768, 32767]
            if audio.dtype == np.float32 or audio.dtype == np.float64:
                # Ensure audio is in [-1, 1] range first
                if np.max(np.abs(audio)) > 1.0:
                    audio = audio / np.max(np.abs(audio))
                audio = (audio * 32767).astype(np.int16)
            else:
                # For other integer types, convert directly
                audio = audio.astype(np.int16)
        
        return audio, sr
        
    except Exception as e:
        logger.error(f"Error loading audio file {file_path}: {e}")
        raise

def convert_pcm16_to_float32(audio: np.ndarray) -> np.ndarray:
    return audio.astype(np.float32) / 32767.0

def main():
    """Main function to demonstrate voice ID capabilities"""
    logger.info("Starting simplified ECAPA voice ID demo")
    voice_id_manager = VoiceIdManager(logger)
    
    logger.info("="*80)
    logger.info("Phase 1: Enrollment")
    logger.info("="*80)
    if len(voice_id_manager.speaker_verifier.get_enrolled_speakers()) > 0:
        logger.info("Existing profiles detected in tmp/users. Skipping enrollment and loading profiles from disk.")
    else:
        enroll_dir = Path("tmp/samples/enroll")
        enroll_files = list(enroll_dir.glob("*.wav"))
        
        for audio_file in enroll_files:
            logger.info(f"Enrolling: {audio_file.name}")
            pcm16_audio, _ = load_audio_as_pcm16(str(audio_file))
            voice_id_manager.enroll_speaker(audio_file.stem[:-1], pcm16_audio)

    enrolled_speakers = voice_id_manager.speaker_verifier.get_enrolled_speakers()
    for speaker_id in enrolled_speakers:
        sample_count = voice_id_manager.speaker_verifier.get_speaker_sample_count(speaker_id)
        logger.info(f"  {speaker_id}: {sample_count} sample(s)")

    logger.info("="*80)
    logger.info("Phase 2: Testing")
    logger.info("="*80)
    test_dir = Path("tmp/samples/test")
    test_files = list(test_dir.glob("*.wav"))

    for audio_file in test_files:
        pcm16_audio, sr = load_audio_as_pcm16(str(audio_file))
        
        id_result = voice_id_manager.identify_speaker(pcm16_audio)

        expected_speaker = audio_file.stem[:-1]
        is_ok = id_result['user_id'] == expected_speaker
        status = "[ OK  ]" if is_ok else "[ISSUE]"

        logger.info(f"{status} {audio_file.name} \tis: {id_result['user_id']} \t(similarity: {id_result['similarity']:.3f}, confidence: {id_result['confidence_level'][0].upper()}) \t{id_result['processing_time']:.2f}ms")

        

if __name__ == "__main__":
    main()
