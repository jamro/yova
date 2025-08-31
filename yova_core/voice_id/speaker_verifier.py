#!/usr/bin/env python3
"""
Speaker verification system using ECAPA embeddings

This module provides the SpeakerVerifier class for speaker recognition and verification
using cosine similarity between ECAPA embeddings with support for ensemble averaging.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Union
import logging

# Set up logging
logger = logging.getLogger(__name__)


class SpeakerVerifier:
    """Speaker verification system using ECAPA embeddings with ensemble averaging"""
    
    def __init__(self, similarity_threshold: float = 0.2868):  # Optimal threshold from analysis
        """
        Initialize speaker verifier
        
        Args:
            similarity_threshold: Threshold for speaker verification (0.0 to 1.0)
        """
        # Store multiple embeddings per speaker for ensemble averaging
        self.enrolled_speakers: Dict[str, List[np.ndarray]] = {}
        self.similarity_threshold = similarity_threshold
        self.confidence_thresholds = {
            'high': 0.6,      # High confidence threshold
            'medium': 0.4,    # Medium confidence threshold  
            'low': 0.2868     # Low confidence threshold (optimal)
        }
        logger.info(f"Speaker verifier initialized with optimal threshold: {similarity_threshold}")
        logger.info(f"Confidence thresholds: High={self.confidence_thresholds['high']:.4f}, "
                   f"Medium={self.confidence_thresholds['medium']:.4f}, "
                   f"Low={self.confidence_thresholds['low']:.4f}")
    
    def enroll_speaker(self, speaker_id: str, embedding: np.ndarray) -> bool:
        """
        Enroll a new speaker with their embedding or add to existing enrollment
        
        Args:
            speaker_id: Unique identifier for the speaker
            embedding: Speaker's embedding vector
            
        Returns:
            True if enrollment successful, False otherwise
        """
        if speaker_id not in self.enrolled_speakers:
            self.enrolled_speakers[speaker_id] = []
            logger.info(f"Creating new enrollment for speaker {speaker_id}")
        
        # Add new embedding to the speaker's collection
        self.enrolled_speakers[speaker_id].append(embedding.copy())
        
        logger.info(f"Speaker {speaker_id} now has {len(self.enrolled_speakers[speaker_id])} samples")
        return True
    
    def enroll_speaker_ensemble(self, speaker_id: str, embeddings: List[np.ndarray]) -> bool:
        """
        Enroll a speaker using multiple audio samples by averaging embeddings
        
        Args:
            speaker_id: Unique identifier for the speaker
            embeddings: List of embedding vectors from different audio samples
            
        Returns:
            True if enrollment successful, False otherwise
        """
        if not embeddings:
            logger.error(f"No embeddings provided for speaker {speaker_id}")
            return False
        
        # Average all embeddings (simple mean)
        avg_embedding = np.mean(embeddings, axis=0)
        
        # Store the averaged embedding as a single sample
        self.enrolled_speakers[speaker_id] = [avg_embedding.copy()]
        
        logger.info(f"Speaker {speaker_id} enrolled with {len(embeddings)} samples (averaged)")
        return True
    
    def get_speaker_embedding(self, speaker_id: str) -> Optional[np.ndarray]:
        """
        Get the averaged embedding for a speaker
        
        Args:
            speaker_id: ID of the speaker
            
        Returns:
            Averaged embedding vector or None if speaker not found
        """
        if speaker_id not in self.enrolled_speakers or not self.enrolled_speakers[speaker_id]:
            return None
        
        embeddings = self.enrolled_speakers[speaker_id]
        
        # If only one embedding, return it directly
        if len(embeddings) == 1:
            return embeddings[0]
        
        # Return averaged embedding
        return np.mean(embeddings, axis=0)
    
    def get_speaker_sample_count(self, speaker_id: str) -> int:
        """
        Get the number of samples enrolled for a speaker
        
        Args:
            speaker_id: ID of the speaker
            
        Returns:
            Number of samples enrolled
        """
        if speaker_id not in self.enrolled_speakers:
            return 0
        return len(self.enrolled_speakers[speaker_id])
    
    def verify_speaker(self, test_embedding: np.ndarray, speaker_id: str) -> Tuple[bool, float, str, float]:
        """
        Verify if test embedding matches enrolled speaker
        
        Args:
            test_embedding: Test embedding to verify
            speaker_id: ID of the speaker to verify against
            
        Returns:
            Tuple of (is_match, similarity_score, confidence_level, confidence_score)
        """
        if speaker_id not in self.enrolled_speakers:
            logger.warning(f"Speaker {speaker_id} not enrolled")
            return False, 0.0, "none", 0.0
        
        # Get averaged embedding for the speaker
        enrolled_embedding = self.get_speaker_embedding(speaker_id)
        if enrolled_embedding is None:
            logger.error(f"No valid embedding found for speaker {speaker_id}")
            return False, 0.0, "none", 0.0
        
        # Validate embeddings
        if len(test_embedding) == 0 or len(enrolled_embedding) == 0:
            logger.error(f"Invalid embedding dimensions: test={len(test_embedding)}, enrolled={len(enrolled_embedding)}")
            return False, 0.0, "none", 0.0
        
        # Calculate cosine similarity properly
        test_norm = np.linalg.norm(test_embedding)
        enrolled_norm = np.linalg.norm(enrolled_embedding)
        
        if test_norm == 0 or enrolled_norm == 0:
            logger.error(f"Zero norm embeddings: test={test_norm:.6f}, enrolled={enrolled_norm:.6f}")
            return False, 0.0, "none", 0.0
        
        similarity = np.dot(test_embedding, enrolled_embedding) / (test_norm * enrolled_norm)
        is_match = similarity > self.similarity_threshold
        
        # Calculate confidence level and score
        confidence_level, confidence_score = self._calculate_confidence(similarity)
        
        sample_count = self.get_speaker_sample_count(speaker_id)
        logger.info(f"Verification {speaker_id}: similarity={similarity:.4f}, match={is_match}, "
                   f"confidence={confidence_level} ({confidence_score:.4f}), samples={sample_count}")
        return is_match, similarity, confidence_level, confidence_score
    
    def _calculate_confidence(self, similarity: float) -> Tuple[str, float]:
        """
        Calculate confidence level and score based on similarity
        
        Args:
            similarity: Cosine similarity score
            
        Returns:
            Tuple of (confidence_level, confidence_score)
        """
        # Normalize similarity to confidence score (0-1)
        # ECAPA scores typically range from -0.1 to 0.8, so we normalize to 0-1
        normalized_similarity = max(0, (similarity + 0.1) / 0.9)
        confidence_score = min(1.0, max(0.0, normalized_similarity))
        
        # Determine confidence level
        if similarity >= self.confidence_thresholds['high']:
            confidence_level = "high"
        elif similarity >= self.confidence_thresholds['medium']:
            confidence_level = "medium"
        elif similarity >= self.confidence_thresholds['low']:
            confidence_level = "low"
        else:
            confidence_level = "none"
        
        return confidence_level, confidence_score
    
    def identify_speaker(self, test_embedding: np.ndarray) -> Tuple[Optional[str], float, str, float]:
        """
        Identify the most likely speaker from enrolled speakers
        
        Args:
            test_embedding: Test embedding to identify
            
        Returns:
            Tuple of (speaker_id, best_similarity, confidence_level, confidence_score) or (None, 0.0, "none", 0.0) if no match
        """
        if not self.enrolled_speakers:
            logger.warning("No speakers enrolled for identification")
            return None, 0.0, "none", 0.0
        
        best_match = None
        best_similarity = -1.0
        
        for speaker_id, enrolled_embeddings in self.enrolled_speakers.items():
            # Get averaged embedding for the speaker
            enrolled_embedding = self.get_speaker_embedding(speaker_id)
            if enrolled_embedding is None:
                logger.warning(f"Skipping {speaker_id} due to no valid embedding")
                continue

            # Validate embeddings
            if len(test_embedding) == 0 or len(enrolled_embedding) == 0:
                logger.warning(f"Skipping {speaker_id} due to invalid embedding dimensions")
                continue
            
            # Calculate cosine similarity properly
            test_norm = np.linalg.norm(test_embedding)
            enrolled_norm = np.linalg.norm(enrolled_embedding)
            
            if test_norm == 0 or enrolled_norm == 0:
                logger.warning(f"Skipping {speaker_id} due to zero norm embeddings")
                continue
            
            similarity = np.dot(test_embedding, enrolled_embedding) / (test_norm * enrolled_norm)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = speaker_id
        
        # Check if best match meets threshold
        if best_similarity > self.similarity_threshold:
            confidence_level, confidence_score = self._calculate_confidence(best_similarity)
            logger.info(f"Speaker identified: {best_match} (similarity: {best_similarity:.4f}, "
                       f"confidence: {confidence_level} ({confidence_score:.4f}))")
            return best_match, best_similarity, confidence_level, confidence_score
        else:
            logger.info(f"No speaker match found (best similarity: {best_similarity:.4f})")
            return None, best_similarity, "none", 0.0
    
    def get_enrolled_speakers(self) -> List[str]:
        """Get list of enrolled speaker IDs"""
        return list(self.enrolled_speakers.keys())
    
    def remove_speaker(self, speaker_id: str) -> bool:
        """Remove a speaker from enrollment"""
        if speaker_id in self.enrolled_speakers:
            del self.enrolled_speakers[speaker_id]
            logger.info(f"Speaker {speaker_id} removed from enrollment")
            return True
        return False
    
    def get_confidence_statistics(self, similarities: List[float]) -> Dict[str, Dict[str, float]]:
        """
        Get confidence statistics for a list of similarity scores
        
        Args:
            similarities: List of similarity scores
            
        Returns:
            Dictionary with confidence level statistics
        """
        if not similarities:
            return {}
        
        stats = {}
        for level in ['high', 'medium', 'low']:
            threshold = self.confidence_thresholds[level]
            count = sum(1 for s in similarities if s >= threshold)
            percentage = 100 * count / len(similarities)
            stats[level] = {
                'count': count,
                'total': len(similarities),
                'percentage': percentage,
                'threshold': threshold
            }
        
        return stats
    
    def get_speaker_statistics(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """
        Get statistics about enrolled speakers and their samples
        
        Returns:
            Dictionary with speaker statistics
        """
        stats = {}
        for speaker_id, embeddings in self.enrolled_speakers.items():
            if not embeddings:
                continue
                
            # Calculate embedding statistics
            embeddings_array = np.array(embeddings)
            sample_count = len(embeddings)
            
            # Calculate variance across samples (lower is better - more consistent)
            if sample_count > 1:
                variance = np.var(embeddings_array, axis=0).mean()
                consistency_score = 1.0 / (1.0 + variance)  # Higher is better
            else:
                variance = 0.0
                consistency_score = 1.0
            
            # Get averaged embedding norm
            avg_embedding = self.get_speaker_embedding(speaker_id)
            avg_norm = np.linalg.norm(avg_embedding) if avg_embedding is not None else 0.0
            
            stats[speaker_id] = {
                'sample_count': sample_count,
                'variance': variance,
                'consistency_score': consistency_score,
                'avg_embedding_norm': avg_norm
            }
        
        return stats
    
    def remove_speaker_sample(self, speaker_id: str, sample_index: int = -1) -> bool:
        """
        Remove a specific sample from a speaker's enrollment
        
        Args:
            speaker_id: ID of the speaker
            sample_index: Index of sample to remove (default: -1 for last sample)
            
        Returns:
            True if sample removed successfully, False otherwise
        """
        if speaker_id not in self.enrolled_speakers:
            return False
        
        embeddings = self.enrolled_speakers[speaker_id]
        if not embeddings:
            return False
        
        try:
            removed_embedding = embeddings.pop(sample_index)
            logger.info(f"Removed sample {sample_index} from speaker {speaker_id}")
            
            # If no samples left, remove the speaker entirely
            if not embeddings:
                del self.enrolled_speakers[speaker_id]
                logger.info(f"Speaker {speaker_id} removed (no samples left)")
            
            return True
        except IndexError:
            logger.error(f"Sample index {sample_index} out of range for speaker {speaker_id}")
            return False
    
    def clear_speaker_samples(self, speaker_id: str) -> bool:
        """
        Clear all samples for a speaker but keep the speaker ID
        
        Args:
            speaker_id: ID of the speaker
            
        Returns:
            True if samples cleared successfully, False otherwise
        """
        if speaker_id in self.enrolled_speakers:
            self.enrolled_speakers[speaker_id].clear()
            logger.info(f"Cleared all samples for speaker {speaker_id}")
            return True
        return False
    
    def get_total_samples(self) -> int:
        """Get total number of samples across all speakers"""
        total = 0
        for embeddings in self.enrolled_speakers.values():
            total += len(embeddings)
        return total
