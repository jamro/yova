#!/usr/bin/env python3
"""
Example script demonstrating ensemble averaging for speaker enrollment

This script shows how to use the new ensemble averaging features in SpeakerVerifier
to enroll speakers with multiple audio samples for more robust recognition.
"""

import numpy as np
import logging
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_embeddings(dimension: int = 192, num_samples: int = 3, noise_level: float = 0.1) -> List[np.ndarray]:
    """
    Create sample embeddings for demonstration purposes
    
    Args:
        dimension: Embedding dimension
        num_samples: Number of samples to create
        noise_level: Amount of noise to add between samples
        
    Returns:
        List of sample embeddings
    """
    # Create a base embedding
    base_embedding = np.random.randn(dimension)
    base_embedding = base_embedding / np.linalg.norm(base_embedding)  # Normalize
    
    embeddings = []
    for i in range(num_samples):
        # Add some noise to simulate different recording conditions
        noise = np.random.randn(dimension) * noise_level
        sample_embedding = base_embedding + noise
        sample_embedding = sample_embedding / np.linalg.norm(sample_embedding)  # Renormalize
        embeddings.append(sample_embedding)
    
    return embeddings


def demonstrate_ensemble_averaging():
    """Demonstrate the ensemble averaging functionality"""
    logger.info("=== Ensemble Averaging Demonstration ===")
    
    # Initialize speaker verifier
    verifier = SpeakerVerifier(similarity_threshold=0.2868)
    
    # Create sample embeddings for two speakers
    speaker1_samples = create_sample_embeddings(dimension=192, num_samples=3, noise_level=0.05)
    speaker2_samples = create_sample_embeddings(dimension=192, num_samples=2, noise_level=0.08)
    
    logger.info(f"Created {len(speaker1_samples)} samples for Speaker 1")
    logger.info(f"Created {len(speaker2_samples)} samples for Speaker 2")
    
    # Method 1: Progressive enrollment (add samples one by one)
    logger.info("\n--- Method 1: Progressive Enrollment ---")
    for i, embedding in enumerate(speaker1_samples):
        verifier.enroll_speaker("speaker_1", embedding)
        logger.info(f"Added sample {i+1} for speaker_1")
    
    # Method 2: Ensemble enrollment (provide all samples at once)
    logger.info("\n--- Method 2: Ensemble Enrollment ---")
    verifier.enroll_speaker_ensemble("speaker_2", speaker2_samples)
    
    # Show enrollment status
    logger.info("\n--- Enrollment Status ---")
    enrolled_speakers = verifier.get_enrolled_speakers()
    for speaker_id in enrolled_speakers:
        sample_count = verifier.get_speaker_sample_count(speaker_id)
        logger.info(f"Speaker {speaker_id}: {sample_count} samples")
    
    # Test verification with a new sample
    logger.info("\n--- Verification Test ---")
    test_embedding = create_sample_embeddings(dimension=192, num_samples=1, noise_level=0.06)[0]
    
    # Verify against both speakers
    for speaker_id in enrolled_speakers:
        is_match, similarity, confidence_level, confidence_score = verifier.verify_speaker(test_embedding, speaker_id)
        logger.info(f"Verification {speaker_id}: match={is_match}, similarity={similarity:.4f}, "
                   f"confidence={confidence_level} ({confidence_score:.4f})")
    
    # Test speaker identification
    logger.info("\n--- Speaker Identification Test ---")
    identified_speaker, similarity, confidence_level, confidence_score = verifier.identify_speaker(test_embedding)
    if identified_speaker:
        logger.info(f"Identified as: {identified_speaker} (similarity: {similarity:.4f}, "
                   f"confidence: {confidence_level} ({confidence_score:.4f}))")
    else:
        logger.info(f"No speaker match found (best similarity: {similarity:.4f})")
    
    # Show detailed statistics
    logger.info("\n--- Speaker Statistics ---")
    stats = verifier.get_speaker_statistics()
    for speaker_id, speaker_stats in stats.items():
        logger.info(f"Speaker {speaker_id}:")
        logger.info(f"  Sample count: {speaker_stats['sample_count']}")
        logger.info(f"  Variance: {speaker_stats['variance']:.6f}")
        logger.info(f"  Consistency score: {speaker_stats['consistency_score']:.4f}")
        logger.info(f"  Average embedding norm: {speaker_stats['avg_embedding_norm']:.6f}")
    
    # Demonstrate sample management
    logger.info("\n--- Sample Management ---")
    total_samples = verifier.get_total_samples()
    logger.info(f"Total samples across all speakers: {total_samples}")
    
    # Remove a sample from speaker_1
    if verifier.get_speaker_sample_count("speaker_1") > 1:
        verifier.remove_speaker_sample("speaker_1", -1)  # Remove last sample
        logger.info("Removed last sample from speaker_1")
        logger.info(f"Speaker_1 now has {verifier.get_speaker_sample_count('speaker_1')} samples")


def demonstrate_quality_improvement():
    """Demonstrate how multiple samples improve verification quality"""
    logger.info("\n=== Quality Improvement Demonstration ===")
    
    verifier = SpeakerVerifier(similarity_threshold=0.2868)
    
    # Create a base speaker with varying quality samples
    base_embedding = np.random.randn(192)
    base_embedding = base_embedding / np.linalg.norm(base_embedding)
    
    # Create samples with different noise levels (simulating different recording conditions)
    high_quality = base_embedding + np.random.randn(192) * 0.02  # Low noise
    medium_quality = base_embedding + np.random.randn(192) * 0.05  # Medium noise
    low_quality = base_embedding + np.random.randn(192) * 0.10   # High noise
    
    # Normalize all samples
    high_quality = high_quality / np.linalg.norm(high_quality)
    medium_quality = medium_quality / np.linalg.norm(medium_quality)
    low_quality = low_quality / np.linalg.norm(low_quality)
    
    # Test single sample enrollment
    logger.info("--- Single Sample Enrollment ---")
    verifier.enroll_speaker("single_sample", high_quality)
    
    # Test verification
    test_embedding = base_embedding + np.random.randn(192) * 0.03
    test_embedding = test_embedding / np.linalg.norm(test_embedding)
    
    is_match, similarity, confidence_level, confidence_score = verifier.verify_speaker(test_embedding, "single_sample")
    logger.info(f"Single sample verification: match={is_match}, similarity={similarity:.4f}, "
               f"confidence={confidence_level} ({confidence_score:.4f})")
    
    # Test ensemble enrollment
    logger.info("\n--- Ensemble Enrollment ---")
    verifier.enroll_speaker_ensemble("ensemble_sample", [high_quality, medium_quality, low_quality])
    
    # Test verification against ensemble
    is_match, similarity, confidence_level, confidence_score = verifier.verify_speaker(test_embedding, "ensemble_sample")
    logger.info(f"Ensemble verification: match={is_match}, similarity={similarity:.4f}, "
               f"confidence={confidence_level} ({confidence_score:.4f})")
    
    # Show the improvement
    logger.info(f"\nImprovement: Ensemble enrollment provides more robust verification")


if __name__ == "__main__":
    try:
        demonstrate_ensemble_averaging()
        demonstrate_quality_improvement()
        logger.info("\n=== Demonstration Complete ===")
    except Exception as e:
        logger.error(f"Error during demonstration: {e}")
        raise
