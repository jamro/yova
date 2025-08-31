#!/usr/bin/env python3
"""
Simplified Speaker Verification System

This module provides the SpeakerVerifier class for speaker recognition and verification
using cosine similarity between ECAPA embeddings.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import logging
import os
import json
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeakerVerifier:
    """Speaker verification system using ECAPA embeddings with file-based storage"""
    
    def __init__(self, similarity_threshold: float = 0.2868, storage_dir: str = None):
        """
        Initialize speaker verifier
        
        Args:
            similarity_threshold: Threshold for speaker verification (0.0 to 1.0)
            storage_dir: Directory to store user profiles (relative to project root), or None to disable storage
        """
        self.enrolled_speakers: Dict[str, List[np.ndarray]] = {}
        self.similarity_threshold = similarity_threshold
        
        # Setup storage directory
        if storage_dir is None:
            self.storage_dir = None
            self.storage_enabled = False
            logger.info(f"Speaker verifier initialized with threshold: {similarity_threshold}")
            logger.info("File storage disabled")
        else:
            self.storage_enabled = True
            self.storage_dir = Path(storage_dir)
            if not self.storage_dir.is_absolute():
                # Get project root (assuming this file is in yova_core/voice_id/)
                project_root = Path(__file__).parent.parent.parent
                self.storage_dir = project_root / storage_dir
            
            # Ensure storage directory exists
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Speaker verifier initialized with threshold: {similarity_threshold}")
            logger.info(f"Storage directory: {self.storage_dir}")
            
            # Load existing profiles
            self._load_all_profiles()
    
    def _get_profile_path(self, speaker_id: str) -> Path:
        """Get the file path for a speaker's profile"""
        if not self.storage_enabled:
            raise RuntimeError("Storage is disabled")
        
        # Sanitize speaker_id to create safe filename
        safe_id = "".join(c for c in speaker_id if c.isalnum() or c in ('-', '_')).rstrip()
        if not safe_id:
            safe_id = f"speaker_{hash(speaker_id) % 10000}"
        return self.storage_dir / f"{safe_id}.pkl"
    
    def _save_profile(self, speaker_id: str) -> bool:
        """
        Save a speaker's profile to disk
        
        Args:
            speaker_id: ID of the speaker to save
            
        Returns:
            True if save successful, False otherwise
        """
        if not self.storage_enabled:
            return True  # Consider it successful if storage is disabled
        
        try:
            if speaker_id not in self.enrolled_speakers:
                return False
            
            profile_path = self._get_profile_path(speaker_id)
            profile_data = {
                'speaker_id': speaker_id,
                'embeddings': self.enrolled_speakers[speaker_id],
                'metadata': {
                    'sample_count': len(self.enrolled_speakers[speaker_id]),
                    'created_at': None,  # Could be enhanced with timestamps
                    'last_updated': None
                }
            }
            
            with open(profile_path, 'wb') as f:
                pickle.dump(profile_data, f)
            
            logger.debug(f"Saved profile for speaker {speaker_id} to {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save profile for speaker {speaker_id}: {e}")
            return False
    
    def _load_profile(self, profile_path: Path) -> bool:
        """
        Load a speaker's profile from disk
        
        Args:
            profile_path: Path to the profile file
            
        Returns:
            True if load successful, False otherwise
        """
        if not self.storage_enabled:
            return False  # Cannot load if storage is disabled
        
        try:
            with open(profile_path, 'rb') as f:
                profile_data = pickle.load(f)
            
            speaker_id = profile_data['speaker_id']
            embeddings = profile_data['embeddings']
            
            # Convert back to numpy arrays if needed
            if embeddings and not isinstance(embeddings[0], np.ndarray):
                embeddings = [np.array(emb) for emb in embeddings]
            
            self.enrolled_speakers[speaker_id] = embeddings
            logger.debug(f"Loaded profile for speaker {speaker_id} from {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load profile from {profile_path}: {e}")
            return False
    
    def _load_all_profiles(self) -> int:
        """
        Load all speaker profiles from disk
        
        Returns:
            Number of profiles loaded
        """
        if not self.storage_enabled:
            return 0
        
        loaded_count = 0
        
        if not self.storage_dir.exists():
            logger.info(f"Storage directory {self.storage_dir} does not exist, creating...")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        for profile_file in self.storage_dir.glob("*.pkl"):
            if self._load_profile(profile_file):
                loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} speaker profiles from disk")
        return loaded_count
    
    def save_all_profiles(self) -> int:
        """
        Save all speaker profiles to disk
        
        Returns:
            Number of profiles saved
        """
        if not self.storage_enabled:
            logger.info("Storage is disabled, no profiles saved")
            return 0
        
        saved_count = 0
        
        for speaker_id in self.enrolled_speakers:
            if self._save_profile(speaker_id):
                saved_count += 1
        
        logger.info(f"Saved {saved_count} speaker profiles to disk")
        return saved_count
    
    def export_profile_metadata(self, output_file: str = None) -> Dict:
        """
        Export metadata about all stored profiles
        
        Args:
            output_file: Optional JSON file to save metadata to
            
        Returns:
            Dictionary containing profile metadata
        """
        metadata = {
            'total_speakers': len(self.enrolled_speakers),
            'total_samples': self.get_total_samples(),
            'storage_enabled': self.storage_enabled,
            'storage_directory': str(self.storage_dir) if self.storage_enabled else None,
            'profiles': {}
        }
        
        if self.storage_enabled:
            for speaker_id in self.enrolled_speakers:
                try:
                    profile_path = self._get_profile_path(speaker_id)
                    metadata['profiles'][speaker_id] = {
                        'sample_count': len(self.enrolled_speakers[speaker_id]),
                        'profile_file': str(profile_path),
                        'file_exists': profile_path.exists(),
                        'file_size': profile_path.stat().st_size if profile_path.exists() else 0
                    }
                except RuntimeError:
                    # Storage disabled
                    metadata['profiles'][speaker_id] = {
                        'sample_count': len(self.enrolled_speakers[speaker_id]),
                        'profile_file': None,
                        'file_exists': False,
                        'file_size': 0
                    }
        else:
            # Storage disabled - just include basic info
            for speaker_id in self.enrolled_speakers:
                metadata['profiles'][speaker_id] = {
                    'sample_count': len(self.enrolled_speakers[speaker_id]),
                    'profile_file': None,
                    'file_exists': False,
                    'file_size': 0
                }
        
        if output_file and self.storage_enabled:
            try:
                with open(output_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"Exported profile metadata to {output_file}")
            except Exception as e:
                logger.error(f"Failed to export metadata to {output_file}: {e}")
        
        return metadata
    
    def backup_profiles(self, backup_dir: str = None) -> bool:
        """
        Create a backup of all speaker profiles
        
        Args:
            backup_dir: Directory to store backup (defaults to tmp/users/backup)
            
        Returns:
            True if backup successful, False otherwise
        """
        if not self.storage_enabled:
            logger.info("Storage is disabled, no backup created")
            return False
        
        if backup_dir is None:
            backup_dir = self.storage_dir / "backup"
        
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save all current profiles
            self.save_all_profiles()
            
            # Copy profile files to backup directory
            copied_count = 0
            for profile_file in self.storage_dir.glob("*.pkl"):
                if profile_file.name != "backup":  # Skip backup directory itself
                    backup_file = backup_path / profile_file.name
                    import shutil
                    shutil.copy2(profile_file, backup_file)
                    copied_count += 1
            
            logger.info(f"Backed up {copied_count} profiles to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def cleanup_orphaned_profiles(self) -> int:
        """
        Remove profile files for speakers that are no longer in memory
        
        Returns:
            Number of orphaned profiles removed
        """
        if not self.storage_enabled:
            logger.info("Storage is disabled, no cleanup performed")
            return 0
        
        removed_count = 0
        
        for profile_file in self.storage_dir.glob("*.pkl"):
            if profile_file.name == "backup":  # Skip backup directory
                continue
                
            # Extract speaker_id from filename
            speaker_id = profile_file.stem
            
            # Check if this speaker is still in memory
            if speaker_id not in self.enrolled_speakers:
                try:
                    profile_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned profile: {profile_file}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned profile {profile_file}: {e}")
        
        logger.info(f"Cleaned up {removed_count} orphaned profile files")
        return removed_count
    
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
        
        # Auto-save the profile
        self._save_profile(speaker_id)
        
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
    
    def get_storage_stats(self) -> Dict:
        """
        Get statistics about the storage system
        
        Returns:
            Dictionary containing storage statistics
        """
        stats = {
            'storage_enabled': self.storage_enabled,
            'storage_directory': str(self.storage_dir) if self.storage_enabled else None,
            'total_speakers': len(self.enrolled_speakers),
            'total_samples': self.get_total_samples(),
            'disk_profiles': 0,
            'total_disk_size': 0,
            'orphaned_files': 0
        }
        
        if self.storage_enabled and self.storage_dir.exists():
            for profile_file in self.storage_dir.glob("*.pkl"):
                if profile_file.name != "backup":
                    stats['disk_profiles'] += 1
                    stats['total_disk_size'] += profile_file.stat().st_size
                    
                    # Check if this file corresponds to a speaker in memory
                    speaker_id = profile_file.stem
                    if speaker_id not in self.enrolled_speakers:
                        stats['orphaned_files'] += 1
        
        return stats
    
    def profile_exists_on_disk(self, speaker_id: str) -> bool:
        """
        Check if a speaker's profile exists on disk
        
        Args:
            speaker_id: ID of the speaker to check
            
        Returns:
            True if profile file exists, False otherwise
        """
        if not self.storage_enabled:
            return False
        
        try:
            profile_path = self._get_profile_path(speaker_id)
            return profile_path.exists()
        except RuntimeError:
            return False
    
    def reload_profile(self, speaker_id: str) -> bool:
        """
        Reload a specific speaker's profile from disk
        
        Args:
            speaker_id: ID of the speaker to reload
            
        Returns:
            True if reload successful, False otherwise
        """
        if not self.storage_enabled:
            return False
        
        try:
            profile_path = self._get_profile_path(speaker_id)
            if profile_path.exists():
                return self._load_profile(profile_path)
        except RuntimeError:
            pass
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
        
        samples = self.enrolled_speakers[speaker_id]
        if 0 <= index < len(samples):
            samples.pop(index)
            # Auto-save the profile after modification
            self._save_profile(speaker_id)
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
            if self.storage_enabled:
                try:
                    profile_path = self._get_profile_path(speaker_id)
                    if profile_path.exists():
                        profile_path.unlink()
                        logger.debug(f"Removed profile file for speaker {speaker_id}")
                except Exception as e:
                    logger.error(f"Failed to remove profile file for speaker {speaker_id}: {e}")
            
            logger.info(f"Cleared all samples for speaker {speaker_id}")
            return True
        
        return False
