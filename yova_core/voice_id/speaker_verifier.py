#!/usr/bin/env python3
"""
Simplified Speaker Verification System

This module provides the SpeakerVerifier class for speaker recognition and verification
using cosine similarity between ECAPA embeddings.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SpeakerVerifier:
    """Speaker verification system using ECAPA embeddings"""
    
    def __init__(self, similarity_threshold: float = 0.2868):
        """
        Initialize speaker verifier
        
        Args:
            similarity_threshold: Threshold for speaker verification (0.0 to 1.0)
        """
        self.enrolled_speakers: Dict[str, List[np.ndarray]] = {}
        self.similarity_threshold = similarity_threshold
        logger.info(f"Speaker verifier initialized with threshold: {similarity_threshold}")
    
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
        
        # Add new embedding to the speaker's collection
        self.enrolled_speakers[speaker_id].append(embedding.copy())
        
        logger.info(f"Speaker {speaker_id} now has {len(self.enrolled_speakers[speaker_id])} samples")
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
            return embeddings[0].copy()
        
        # Average multiple embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        # Renormalize
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        return avg_embedding
    
    def verify_speaker(self, test_embedding: np.ndarray, speaker_id: str) -> Tuple[bool, float, str, float]:
        """
        Verify if test embedding matches enrolled speaker
        
        Args:
            test_embedding: Test embedding to verify
            speaker_id: ID of the speaker to verify against
            
        Returns:
            Tuple of (is_match, similarity, confidence_level, confidence_score)
        """
        if speaker_id not in self.enrolled_speakers:
            return False, 0.0, "unknown", 0.0
        
        # Get best similarity across all samples
        similarities = []
        for enrolled_embedding in self.enrolled_speakers[speaker_id]:
            similarity = self._cosine_similarity(test_embedding, enrolled_embedding)
            similarities.append(similarity)
        
        best_similarity = max(similarities)
        is_match = best_similarity >= self.similarity_threshold
        
        # Simple confidence based on similarity
        if best_similarity >= 0.6:
            confidence_level = "high"
        elif best_similarity >= 0.4:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        return is_match, best_similarity, confidence_level, best_similarity
    
    def identify_speaker(self, test_embedding: np.ndarray) -> Tuple[Optional[str], float, str, float]:
        """
        Identify the most likely speaker from all enrolled speakers
        
        Args:
            test_embedding: Test embedding to identify
            
        Returns:
            Tuple of (speaker_id, similarity, confidence_level, confidence_score)
        """
        if not self.enrolled_speakers:
            return None, 0.0, "unknown", 0.0
        
        best_speaker = None
        best_similarity = -1.0
        
        for speaker_id in self.enrolled_speakers:
            is_match, similarity, _, _ = self.verify_speaker(test_embedding, speaker_id)
            if similarity > best_similarity:
                best_similarity = similarity
                best_speaker = speaker_id
        
        if best_similarity >= self.similarity_threshold:
            confidence_level = "high" if best_similarity >= 0.6 else "medium"
            return best_speaker, best_similarity, confidence_level, best_similarity
        
        return None, best_similarity, "low", best_similarity
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def get_enrolled_speakers(self) -> List[str]:
        """
        Get list of enrolled speaker IDs
        
        Returns:
            List of speaker IDs
        """
        return list(self.enrolled_speakers.keys())
    
    def get_speaker_sample_count(self, speaker_id: str) -> int:
        """
        Get number of samples for a speaker
        
        Args:
            speaker_id: ID of the speaker
            
        Returns:
            Number of samples for the speaker
        """
        return len(self.enrolled_speakers.get(speaker_id, []))
    
    def get_total_samples(self) -> int:
        """
        Get total number of samples across all speakers
        
        Returns:
            Total sample count
        """
        return sum(len(samples) for samples in self.enrolled_speakers.values())
    
    def remove_speaker_sample(self, speaker_id: str, index: int) -> bool:
        """
        Remove a specific sample from a speaker
        
        Args:
            speaker_id: ID of the speaker
            index: Index of the sample to remove
            
        Returns:
            True if sample removed successfully, False otherwise
        """
        if speaker_id not in self.enrolled_speakers:
            return False
        
        samples = self.enrolled_speakers[speaker_id]
        if 0 <= index < len(samples):
            samples.pop(index)
            logger.info(f"Removed sample {index} from speaker {speaker_id}")
            return True
        
        return False
    
    def clear_speaker(self, speaker_id: str) -> bool:
        """
        Remove all samples for a speaker
        
        Args:
            speaker_id: ID of the speaker to clear
            
        Returns:
            True if speaker cleared successfully, False otherwise
        """
        if speaker_id in self.enrolled_speakers:
            del self.enrolled_speakers[speaker_id]
            logger.info(f"Cleared all samples for speaker {speaker_id}")
            return True
        
        return False
