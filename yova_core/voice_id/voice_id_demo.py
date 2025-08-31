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
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
from yova_core.voice_id.ecapa_model import ECAPAModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_audio_as_pcm16(file_path: str) -> tuple[np.ndarray, int]:
    """
    Load audio file and convert to PCM 16-bit format (same as transcriber)
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Tuple of (audio_data, sample_rate)
        audio_data: PCM 16-bit format (int16) at 16kHz mono
    """
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
    """
    Convert PCM 16-bit audio to float32 in [-1, 1] range for ECAPA model
    
    Args:
        audio: PCM 16-bit audio data (int16)
        
    Returns:
        Float32 audio data in [-1, 1] range
    """
    # Convert from int16 [-32768, 32767] to float32 [-1, 1]
    return audio.astype(np.float32) / 32767.0


def main():
    """Main function to demonstrate voice ID capabilities"""
    logger.info("Starting simplified ECAPA voice ID demo")
    
    # Initialize components (no preprocessor needed)
    ecapa_model = ECAPAModel()
    speaker_verifier = SpeakerVerifier()
    
    # Phase 1: Enroll users from tmp/samples/enroll directory
    enroll_dir = Path("tmp/samples/enroll")
    enroll_files = list(enroll_dir.glob("*.wav"))
    
    if not enroll_files:
        logger.error("No audio files found in tmp/samples/enroll directory")
        return
    
    logger.info(f"Phase 1: Enrollment - Found {len(enroll_files)} audio files")
    
    # Process each enrollment audio file
    enrollment_results = []
    
    for audio_file in enroll_files:
        try:
            logger.info(f"Enrolling: {audio_file.name}")
            
            # Load audio as PCM 16-bit format (same as transcriber)
            pcm16_audio, sr = load_audio_as_pcm16(str(audio_file))
            logger.info(f"  Loaded: {len(pcm16_audio)} samples, {sr}Hz, PCM16 format")
            
            # Convert to float32 for ECAPA model
            float32_audio = convert_pcm16_to_float32(pcm16_audio)
            logger.info(f"  Converted to float32: range [{float32_audio.min():.3f}, {float32_audio.max():.3f}]")
            
            # Extract embedding using float32 audio
            embedding = ecapa_model.extract_embedding(float32_audio, sr)
            
            if len(embedding) == 0:
                logger.error(f"Failed to extract embedding for {audio_file.name}")
                continue
            
            # Store enrollment results
            result = {
                'file_path': str(audio_file),
                'pcm16_audio': pcm16_audio,
                'float32_audio': float32_audio,
                'embedding': embedding,
                'sample_rate': sr,
                'duration': len(pcm16_audio) / sr
            }
            enrollment_results.append(result)
            
            # Extract speaker ID from filename (remove last character)
            speaker_id = audio_file.stem[:-1]
            
            # Enroll speaker
            speaker_verifier.enroll_speaker(speaker_id, embedding)
            logger.info(f"Speaker enrolled: {speaker_id}")
            
        except Exception as e:
            logger.error(f"Error processing enrollment file {audio_file}: {e}")
            continue
    
    # Show enrollment status
    if enrollment_results:
        logger.info(f"\nEnrollment Summary:")
        enrolled_speakers = speaker_verifier.get_enrolled_speakers()
        for speaker_id in enrolled_speakers:
            sample_count = speaker_verifier.get_speaker_sample_count(speaker_id)
            logger.info(f"  {speaker_id}: {sample_count} sample(s)")
        
        # Phase 2: Test enrolled users with files from tmp/samples/test directory
        test_dir = Path("tmp/samples/test")
        test_files = list(test_dir.glob("*.wav"))
        
        if not test_files:
            logger.warning("No test files found in tmp/samples/test directory")
            logger.info("Voice ID demo completed (enrollment only)")
            return
        
        logger.info(f"\nPhase 2: Testing - Found {len(test_files)} test audio files")
        
        # Process each test audio file
        test_results = []
        
        for audio_file in test_files:
            try:
                logger.info(f"Testing: {audio_file.name}")
                
                # Load audio as PCM 16-bit format
                pcm16_audio, sr = load_audio_as_pcm16(str(audio_file))
                logger.info(f"  Loaded: {len(pcm16_audio)} samples, {sr}Hz, PCM16 format")
                
                # Convert to float32 for ECAPA model
                float32_audio = convert_pcm16_to_float32(pcm16_audio)
                logger.info(f"  Converted to float32: range [{float32_audio.min():.3f}, {float32_audio.max():.3f}]")
                
                # Extract embedding using float32 audio
                embedding = ecapa_model.extract_embedding(float32_audio, sr)
                
                if len(embedding) == 0:
                    logger.error(f"Failed to extract embedding for {audio_file.name}")
                    continue
                
                # Store test results
                result = {
                    'file_path': str(audio_file),
                    'pcm16_audio': pcm16_audio,
                    'float32_audio': float32_audio,
                    'embedding': embedding,
                    'sample_rate': sr,
                    'duration': len(pcm16_audio) / sr
                }
                test_results.append(result)
                
                # Test speaker identification
                identified_speaker, similarity, confidence_level, _ = speaker_verifier.identify_speaker(embedding)
                
                if identified_speaker:
                    logger.info(f"  {audio_file.name} identified as: {identified_speaker} "
                               f"(similarity: {similarity:.3f}, confidence: {confidence_level})")
                else:
                    logger.info(f"  {audio_file.name}: No speaker match found (best similarity: {similarity:.3f})")
                
            except Exception as e:
                logger.error(f"Error processing test file {audio_file}: {e}")
                continue
        
        # User comparison statistics (enrollment vs test)
        if enrollment_results and test_results:
            logger.info(f"\n{'='*50}")
            logger.info("Enrollment vs Test Comparison Statistics")
            logger.info(f"{'='*50}")
            
            # Extract user IDs from filenames (remove last 5 chars: .wav + number)
            enrollment_user_ids = []
            for result in enrollment_results:
                filename = Path(result['file_path']).name
                user_id = filename[:-5]  # Remove last 5 characters (.wav + number)
                enrollment_user_ids.append({
                    'filename': filename,
                    'user_id': user_id,
                    'embedding': result['embedding']
                })
            
            test_user_ids = []
            for result in test_results:
                filename = Path(result['file_path']).name
                user_id = filename[:-5]  # Remove last 5 characters (.wav + number)
                test_user_ids.append({
                    'filename': filename,
                    'user_id': user_id,
                    'embedding': result['embedding']
                })
            
            # Group by user ID
            enrollment_user_groups = {}
            for item in enrollment_user_ids:
                user_id = item['user_id']
                if user_id not in enrollment_user_groups:
                    enrollment_user_groups[user_id] = []
                enrollment_user_groups[user_id].append(item)
            
            test_user_groups = {}
            for item in test_user_ids:
                user_id = item['user_id']
                if user_id not in test_user_groups:
                    test_user_groups[user_id] = []
                test_user_groups[user_id].append(item)
            
            logger.info(f"Enrollment users: {len(enrollment_user_groups)} unique user IDs:")
            for user_id, files in enrollment_user_groups.items():
                logger.info(f"  {user_id}: {len(files)} files")
            
            logger.info(f"Test users: {len(test_user_groups)} unique user IDs:")
            for user_id, files in test_user_groups.items():
                logger.info(f"  {user_id}: {len(files)} files")
            
            # Test same-user vs different-user similarities between enrollment and test
            same_user_similarities = []
            different_user_similarities = []
            
            # Compare all enrollment vs test combinations
            for enroll_item in enrollment_user_ids:
                for test_item in test_user_ids:
                    # Calculate cosine similarity
                    emb1 = enroll_item['embedding']
                    emb2 = test_item['embedding']
                    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                    
                    # Categorize by user ID relationship
                    if enroll_item['user_id'] == test_item['user_id']:
                        same_user_similarities.append(similarity)
                        logger.info(f"SAME USER: {enroll_item['filename']} vs {test_item['filename']}: {similarity:.4f}")
                    else:
                        different_user_similarities.append(similarity)
                        logger.info(f"DIFFERENT USER: {enroll_item['filename']} vs {test_item['filename']}: {similarity:.4f}")
            
            # Statistical analysis
            if same_user_similarities:
                logger.info(f"\nSame User Statistics (Enrollment vs Test):")
                logger.info(f"  Count: {len(same_user_similarities)}")
                logger.info(f"  Mean: {np.mean(same_user_similarities):.4f}")
                logger.info(f"  Std: {np.std(same_user_similarities):.4f}")
                logger.info(f"  Min: {np.min(same_user_similarities):.4f}")
                logger.info(f"  Max: {np.max(same_user_similarities):.4f}")
            
            if different_user_similarities:
                logger.info(f"\nDifferent User Statistics (Enrollment vs Test):")
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
    
    logger.info("Voice ID demo completed successfully!")


if __name__ == "__main__":
    main()
