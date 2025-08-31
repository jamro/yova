#!/usr/bin/env python3
"""
Profile Storage Layer for Speaker Verification

This module provides the ProfileStorage class for handling file I/O operations
for speaker profiles, including saving, loading, backup, and cleanup operations.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import os
import json
import pickle
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class ProfileStorage:
    """Handles file-based storage operations for speaker profiles"""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize profile storage
        
        Args:
            storage_dir: Directory to store user profiles (relative to project root), or None to disable storage
        """
        if storage_dir is None:
            self.storage_dir = None
            self.storage_enabled = False
            logger.info("Profile storage disabled")
        else:
            self.storage_enabled = True
            self.storage_dir = Path(storage_dir)
            if not self.storage_dir.is_absolute():
                # Get project root (assuming this file is in yova_core/voice_id/)
                project_root = Path(__file__).parent.parent.parent
                self.storage_dir = project_root / storage_dir
            
            # Ensure storage directory exists
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Profile storage initialized at: {self.storage_dir}")
    
    def _get_profile_path(self, speaker_id: str) -> Path:
        """Get the file path for a speaker's profile"""
        if not self.storage_enabled:
            raise RuntimeError("Storage is disabled")
        
        # Sanitize speaker_id to create safe filename
        safe_id = "".join(c for c in speaker_id if c.isalnum() or c in ('-', '_')).rstrip()
        if not safe_id:
            safe_id = f"speaker_{hash(speaker_id) % 10000}"
        return self.storage_dir / f"{safe_id}.pkl"
    
    def save_profile(self, speaker_id: str, embeddings: List[np.ndarray]) -> bool:
        """
        Save a speaker's profile to disk
        
        Args:
            speaker_id: ID of the speaker to save
            embeddings: List of embeddings to save
            
        Returns:
            True if save successful, False otherwise
        """
        if not self.storage_enabled:
            return True  # Consider it successful if storage is disabled
        
        try:
            profile_path = self._get_profile_path(speaker_id)
            profile_data = {
                'speaker_id': speaker_id,
                'embeddings': embeddings,
                'metadata': {
                    'sample_count': len(embeddings),
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
    
    def load_profile(self, profile_path: Path) -> Tuple[Optional[str], Optional[List[np.ndarray]]]:
        """
        Load a speaker's profile from disk
        
        Args:
            profile_path: Path to the profile file
            
        Returns:
            Tuple of (speaker_id, embeddings) or (None, None) if failed
        """
        if not self.storage_enabled:
            return None, None
        
        try:
            with open(profile_path, 'rb') as f:
                profile_data = pickle.load(f)
            
            speaker_id = profile_data['speaker_id']
            embeddings = profile_data['embeddings']
            
            # Convert back to numpy arrays if needed
            if embeddings and not isinstance(embeddings[0], np.ndarray):
                embeddings = [np.array(emb) for emb in embeddings]
            
            logger.debug(f"Loaded profile for speaker {speaker_id} from {profile_path}")
            return speaker_id, embeddings
            
        except Exception as e:
            logger.error(f"Failed to load profile from {profile_path}: {e}")
            return None, None
    
    def load_all_profiles(self) -> Dict[str, List[np.ndarray]]:
        """
        Load all speaker profiles from disk
        
        Returns:
            Dictionary mapping speaker_id to list of embeddings
        """
        if not self.storage_enabled:
            return {}
        
        loaded_profiles = {}
        
        if not self.storage_dir.exists():
            logger.info(f"Storage directory {self.storage_dir} does not exist, creating...")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            return loaded_profiles
        
        for profile_file in self.storage_dir.glob("*.pkl"):
            speaker_id, embeddings = self.load_profile(profile_file)
            if speaker_id and embeddings:
                loaded_profiles[speaker_id] = embeddings
        
        logger.info(f"Loaded {len(loaded_profiles)} speaker profiles from disk")
        return loaded_profiles
    
    def save_all_profiles(self, enrolled_speakers: Dict[str, List[np.ndarray]]) -> int:
        """
        Save all speaker profiles to disk
        
        Args:
            enrolled_speakers: Dictionary of speaker_id to embeddings
            
        Returns:
            Number of profiles saved
        """
        if not self.storage_enabled:
            logger.info("Storage is disabled, no profiles saved")
            return 0
        
        saved_count = 0
        
        for speaker_id, embeddings in enrolled_speakers.items():
            if self.save_profile(speaker_id, embeddings):
                saved_count += 1
        
        logger.info(f"Saved {saved_count} speaker profiles to disk")
        return saved_count
    
    def backup_profiles(self, backup_dir: str = None) -> bool:
        """
        Create a backup of all speaker profiles
        
        Args:
            backup_dir: Directory to store backup (defaults to storage_dir/backup)
            
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
            # Copy profile files to backup directory
            copied_count = 0
            for profile_file in self.storage_dir.glob("*.pkl"):
                if profile_file.name != "backup":  # Skip backup directory itself
                    backup_file = backup_path / profile_file.name
                    shutil.copy2(profile_file, backup_file)
                    copied_count += 1
            
            logger.info(f"Backed up {copied_count} profiles to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def cleanup_orphaned_profiles(self, enrolled_speakers: Dict[str, List[np.ndarray]]) -> int:
        """
        Remove profile files for speakers that are no longer in memory
        
        Args:
            enrolled_speakers: Dictionary of currently enrolled speakers
            
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
            if speaker_id not in enrolled_speakers:
                try:
                    profile_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned profile: {profile_file}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned profile {profile_file}: {e}")
        
        logger.info(f"Cleaned up {removed_count} orphaned profile files")
        return removed_count
    
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
    
    def reload_profile(self, speaker_id: str) -> Tuple[Optional[str], Optional[List[np.ndarray]]]:
        """
        Reload a specific speaker's profile from disk
        
        Args:
            speaker_id: ID of the speaker to reload
            
        Returns:
            Tuple of (speaker_id, embeddings) or (None, None) if failed
        """
        if not self.storage_enabled:
            return None, None
        
        try:
            profile_path = self._get_profile_path(speaker_id)
            if profile_path.exists():
                return self.load_profile(profile_path)
        except RuntimeError:
            pass
        return None, None
    
    def remove_profile_file(self, speaker_id: str) -> bool:
        """
        Remove a speaker's profile file from disk
        
        Args:
            speaker_id: ID of the speaker whose profile to remove
            
        Returns:
            True if file removed successfully, False otherwise
        """
        if not self.storage_enabled:
            return False
        
        try:
            profile_path = self._get_profile_path(speaker_id)
            if profile_path.exists():
                profile_path.unlink()
                logger.debug(f"Removed profile file for speaker {speaker_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove profile file for speaker {speaker_id}: {e}")
        
        return False
    
    def get_storage_stats(self, enrolled_speakers: Dict[str, List[np.ndarray]]) -> Dict:
        """
        Get statistics about the storage system
        
        Args:
            enrolled_speakers: Dictionary of currently enrolled speakers
            
        Returns:
            Dictionary containing storage statistics
        """
        stats = {
            'storage_enabled': self.storage_enabled,
            'storage_directory': str(self.storage_dir) if self.storage_enabled else None,
            'total_speakers': len(enrolled_speakers),
            'total_samples': sum(len(samples) for samples in enrolled_speakers.values()),
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
                    if speaker_id not in enrolled_speakers:
                        stats['orphaned_files'] += 1
        
        return stats
    
    def export_profile_metadata(self, enrolled_speakers: Dict[str, List[np.ndarray]], 
                               output_file: str = None) -> Dict:
        """
        Export metadata about all stored profiles
        
        Args:
            enrolled_speakers: Dictionary of currently enrolled speakers
            output_file: Optional JSON file to save metadata to
            
        Returns:
            Dictionary containing profile metadata
        """
        metadata = {
            'total_speakers': len(enrolled_speakers),
            'total_samples': sum(len(samples) for samples in enrolled_speakers.values()),
            'storage_enabled': self.storage_enabled,
            'storage_directory': str(self.storage_dir) if self.storage_enabled else None,
            'profiles': {}
        }
        
        if self.storage_enabled:
            for speaker_id in enrolled_speakers:
                try:
                    profile_path = self._get_profile_path(speaker_id)
                    metadata['profiles'][speaker_id] = {
                        'sample_count': len(enrolled_speakers[speaker_id]),
                        'profile_file': str(profile_path),
                        'file_exists': profile_path.exists(),
                        'file_size': profile_path.stat().st_size if profile_path.exists() else 0
                    }
                except RuntimeError:
                    # Storage disabled
                    metadata['profiles'][speaker_id] = {
                        'sample_count': len(enrolled_speakers[speaker_id]),
                        'profile_file': None,
                        'file_exists': False,
                        'file_size': 0
                    }
        else:
            # Storage disabled - just include basic info
            for speaker_id in enrolled_speakers:
                metadata['profiles'][speaker_id] = {
                    'sample_count': len(enrolled_speakers[speaker_id]),
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
