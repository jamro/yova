#!/usr/bin/env python3
"""
Simplified ECAPA Voice ID Demo

This script demonstrates basic voice ID functionality with essential user comparison statistics.
"""

import numpy as np
import soundfile as sf
from pathlib import Path
import logging
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
from yova_core.voice_id.ecapa_model import ECAPAModel
from yova_core.voice_id.ecapa_preprocessor import ECAPAPreprocessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate voice ID capabilities"""
    logger.info("Starting simplified ECAPA voice ID demo")
    
    # Initialize components
    preprocessor = ECAPAPreprocessor()
    ecapa_model = ECAPAModel()
    speaker_verifier = SpeakerVerifier()
    
    # Find audio files in tmp directory
    tmp_dir = Path("tmp/samples")
    audio_files = list(tmp_dir.glob("*.wav"))
    
    if not audio_files:
        logger.error("No audio files found in tmp directory")
        return
    
    logger.info(f"Found {len(audio_files)} audio files")
    
    # Process each audio file
    results = []
    
    for audio_file in audio_files:
        try:
            logger.info(f"Processing: {audio_file.name}")
            
            # Process audio
            mel_spec, model_input, metadata = preprocessor.process_audio(str(audio_file))
            
            # Load raw audio for ECAPA model
            raw_audio, raw_sr = sf.read(str(audio_file))
            if len(raw_audio.shape) > 1:  # Convert stereo to mono
                raw_audio = np.mean(raw_audio, axis=1)
            
            # Extract embedding
            embedding = ecapa_model.extract_embedding(raw_audio, raw_sr)
            
            if len(embedding) == 0:
                logger.error(f"Failed to extract embedding for {audio_file.name}")
                continue
            
            # Store results
            result = {
                'file_path': str(audio_file),
                'embedding': embedding,
                'metadata': metadata
            }
            results.append(result)
            
            # Extract speaker ID from filename (remove last character)
            speaker_id = audio_file.stem[:-1]
            
            # Enroll speaker
            speaker_verifier.enroll_speaker(speaker_id, embedding)
            logger.info(f"Speaker enrolled: {speaker_id}")
            
            # Verify speaker
            is_match, similarity, confidence_level, _ = speaker_verifier.verify_speaker(embedding, speaker_id)
            logger.info(f"Verification: {'✓' if is_match else '✗'} "
                       f"(similarity: {similarity:.3f}, confidence: {confidence_level})")
            
        except Exception as e:
            logger.error(f"Error processing {audio_file}: {e}")
            continue
    
    # Show enrollment status
    if results:
        logger.info(f"\nEnrollment Summary:")
        enrolled_speakers = speaker_verifier.get_enrolled_speakers()
        for speaker_id in enrolled_speakers:
            sample_count = speaker_verifier.get_speaker_sample_count(speaker_id)
            logger.info(f"  {speaker_id}: {sample_count} sample(s)")
        
        # Test speaker identification
        logger.info(f"\nSpeaker Identification Test:")
        test_result = results[0]  # Use first result as test
        test_embedding = test_result['embedding']
        test_file = Path(test_result['file_path']).name
        
        identified_speaker, similarity, confidence_level, _ = speaker_verifier.identify_speaker(test_embedding)
        
        if identified_speaker:
            logger.info(f"  {test_file} identified as: {identified_speaker} "
                       f"(similarity: {similarity:.3f}, confidence: {confidence_level})")
        else:
            logger.info(f"  {test_file}: No speaker match found (best similarity: {similarity:.3f})")
        
        # User comparison statistics (same vs different users)
        if len(results) >= 2:
            logger.info(f"\n{'='*50}")
            logger.info("User Comparison Statistics")
            logger.info(f"{'='*50}")
            
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
