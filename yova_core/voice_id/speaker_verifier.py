#!/usr/bin/env python3
"""
Simplified Speaker Verification System

This module provides the SpeakerVerifier class for speaker recognition and verification
using cosine similarity between ECAPA embeddings.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import logging

from .profile_storage import ProfileStorage
from .speaker_profile import SpeakerProfile

logger = logging.getLogger(__name__)


class SpeakerVerifier:
    """Speaker verification system using ECAPA embeddings with file-based storage"""
    
    def __init__(self, similarity_threshold: float = 0.267, storage_dir: str = None, top_k_mean: int = 3, decision_margin: float = 0.04):
        """
        Initialize speaker verifier
        
        Args:
            similarity_threshold: Threshold for speaker verification (0.0 to 1.0)
            storage_dir: Directory to store user profiles (relative to project root), or None to disable storage
        """
        self.enrolled_speakers: Dict[str, SpeakerProfile] = {}
        self.similarity_threshold = similarity_threshold
        # Scoring and decision parameters
        self.top_k_mean = max(1, int(top_k_mean))
        self.decision_margin = max(0.0, float(decision_margin))
        
        # Initialize storage layer
        self.storage = ProfileStorage(storage_dir)
        
        # Load existing profiles if storage is enabled
        if self.storage.storage_enabled:
            loaded_profiles = self.storage.load_all_profiles()
            # Convert loaded profiles to SpeakerProfile objects
            for speaker_id, embeddings in loaded_profiles.items():
                profile = SpeakerProfile(speaker_id)
                for embedding in embeddings:
                    profile.add_embedding(embedding)
                self.enrolled_speakers[speaker_id] = profile
        
        logger.info(f"Speaker verifier initialized with threshold: {similarity_threshold}")
        logger.info(f"Scoring: top_k_mean={self.top_k_mean}, decision_margin={self.decision_margin:.3f}")
        if self.storage.storage_enabled:
            logger.info(f"Storage directory: {self.storage.storage_dir}")
        else:
            logger.info("File storage disabled")
    def save_all_profiles(self) -> int:
        """
        Save all speaker profiles to disk
        
        Returns:
            Number of profiles saved
        """
        return self.storage.save_all_profiles(self.enrolled_speakers)
    
    def export_profile_metadata(self, output_file: str = None) -> Dict:
        """
        Export metadata about all stored profiles
        
        Args:
            output_file: Optional JSON file to save metadata to
            
        Returns:
            Dictionary containing profile metadata
        """
        return self.storage.export_profile_metadata(self.enrolled_speakers, output_file)
    
    def backup_profiles(self, backup_dir: str = None) -> bool:
        """
        Create a backup of all speaker profiles
        
        Args:
            backup_dir: Directory to store backup (defaults to storage_dir/backup)
            
        Returns:
            True if backup successful, False otherwise
        """
        return self.storage.backup_profiles(backup_dir)
    
    def cleanup_orphaned_profiles(self) -> int:
        """
        Remove profile files for speakers that are no longer in memory
        
        Returns:
            Number of orphaned profiles removed
        """
        return self.storage.cleanup_orphaned_profiles(self.enrolled_speakers)
    
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
            self.enrolled_speakers[speaker_id] = SpeakerProfile(speaker_id)
        
                # Add new embedding to the speaker's profile
        if self.enrolled_speakers[speaker_id].add_embedding(embedding):
            # Auto-save the profile
            self.storage.save_profile(speaker_id, self.enrolled_speakers[speaker_id].get_embeddings_for_storage())
            logger.info(f"Speaker {speaker_id} now has {self.enrolled_speakers[speaker_id].get_sample_count()} samples")
            return True
        
        return False
    
    def get_speaker_embedding(self, speaker_id: str) -> Optional[np.ndarray]:
        """
        Get the averaged embedding for a speaker
        
        Args:
            speaker_id: ID of the speaker
            
        Returns:
            Averaged embedding vector or None if speaker not found
        """
        if speaker_id not in self.enrolled_speakers:
            return None
        
        return self.enrolled_speakers[speaker_id].get_embedding()
    
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
        
        profile = self.enrolled_speakers[speaker_id]
        if not profile.has_embeddings():
            return False, 0.0, "unknown", 0.0
        
        # Compute similarities against all enrollment samples
        similarities = []
        for enrolled_embedding in profile.get_embeddings_list():
            similarity = self._cosine_similarity(test_embedding, enrolled_embedding)
            similarities.append(similarity)
        # Aggregate using top-k mean to reduce variance
        if similarities:
            sorted_sims = sorted(similarities, reverse=True)
            k = min(self.top_k_mean, len(sorted_sims))
            score = float(np.mean(sorted_sims[:k]))
        else:
            score = 0.0
        is_match = score >= self.similarity_threshold
        
        # Simple confidence based on aggregated score
        if score >= 0.6:
            confidence_level = "high"
        elif score >= 0.4:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        return is_match, score, confidence_level, score
    
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
        
        # Collect scores for all speakers (top-k mean per speaker)
        scores = []
        for speaker_id in self.enrolled_speakers:
            _, score, _, _ = self.verify_speaker(test_embedding, speaker_id)
            scores.append((speaker_id, score))
        if not scores:
            return None, 0.0, "low", 0.0
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        best_speaker, best_score = scores[0]
        second_score = scores[1][1] if len(scores) > 1 else -1.0
        
        # Threshold and decision margin check
        if best_score >= self.similarity_threshold:
            if len(scores) == 1 or (best_score - second_score) >= self.decision_margin:
                confidence_level = "high" if best_score >= 0.6 else "medium"
                return best_speaker, best_score, confidence_level, best_score
            # Ambiguous case: margin too small
            return None, best_score, "low", best_score
        
        return None, best_score, "low", best_score
    
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
        if speaker_id not in self.enrolled_speakers:
            return 0
        return self.enrolled_speakers[speaker_id].get_sample_count()
    
    def get_total_samples(self) -> int:
        """
        Get total number of samples across all speakers
        
        Returns:
            Total sample count
        """
        return sum(profile.get_sample_count() for profile in self.enrolled_speakers.values())
    
    def get_storage_stats(self) -> Dict:
        """
        Get statistics about the storage system
        
        Returns:
            Dictionary containing storage statistics
        """
        return self.storage.get_storage_stats(self.enrolled_speakers)
    
    def profile_exists_on_disk(self, speaker_id: str) -> bool:
        """
        Check if a speaker's profile exists on disk
        
        Args:
            speaker_id: ID of the speaker to check
            
        Returns:
            True if profile file exists, False otherwise
        """
        return self.storage.profile_exists_on_disk(speaker_id)
    
    def reload_profile(self, speaker_id: str) -> bool:
        """
        Reload a specific speaker's profile from disk
        
        Args:
            speaker_id: ID of the speaker to reload
            
        Returns:
            True if reload successful, False otherwise
        """
        speaker_id_loaded, embeddings = self.storage.reload_profile(speaker_id)
        if speaker_id_loaded and embeddings:
            profile = SpeakerProfile(speaker_id)
            for embedding in embeddings:
                profile.add_embedding(embedding)
            self.enrolled_speakers[speaker_id] = profile
            return True
        return False
    
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
        
        profile = self.enrolled_speakers[speaker_id]
        if profile.remove_embedding(index):
            # Auto-save the profile after modification
            self.storage.save_profile(speaker_id, profile.get_embeddings_for_storage())
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
            
            # Remove the profile file if storage is enabled
            if self.storage.storage_enabled:
                self.storage.remove_profile_file(speaker_id)
            
            logger.info(f"Cleared all samples for speaker {speaker_id}")
            return True
        
        return False
