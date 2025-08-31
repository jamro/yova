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

import numpy as np
import soundfile as sf
from pathlib import Path

from typing import Tuple, List, Dict
import logging
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
from yova_core.voice_id.ecapa_model import ECAPAModel
from yova_core.voice_id.ecapa_preprocessor import ECAPAPreprocessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        apply_trim=True,
        trim_start_ms=200.0
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
            
            # Extract speaker ID from filename (remove extension and any path)
            speaker_id = audio_file.stem
            
            # Enroll speaker with the new sample
            speaker_verifier.enroll_speaker(speaker_id, embedding)
            logger.info(f"  Speaker enrolled: {speaker_id} (sample {speaker_verifier.get_speaker_sample_count(speaker_id)})")
            
            # Verify speaker against their enrolled samples
            is_match, similarity, confidence_level, confidence_score = speaker_verifier.verify_speaker(embedding, speaker_id)
            
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
        
        # Show enrolled speakers with sample counts
        enrolled_speakers = speaker_verifier.get_enrolled_speakers()
        logger.info(f"Enrolled speakers: {enrolled_speakers}")
        
        # Show sample statistics for each speaker
        for speaker_id in enrolled_speakers:
            sample_count = speaker_verifier.get_speaker_sample_count(speaker_id)
            logger.info(f"  {speaker_id}: {sample_count} sample(s)")
        
        # Show total statistics
        total_samples = speaker_verifier.get_total_samples()
        logger.info(f"Total samples across all speakers: {total_samples}")
        
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
                
                # Interpretation based on ECAPA model performance (aligned with documented ranges)
                if similarity > 0.7:
                    interpretation = "Very similar (likely same speaker)"
                elif similarity > 0.6:
                    interpretation = "Similar (possibly same speaker)"
                elif similarity > 0.5:
                    interpretation = "Moderately similar (could be same speaker)"
                elif similarity > 0.4:
                    interpretation = "Slightly similar (possibly same speaker)"
                elif similarity > 0.3:
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
