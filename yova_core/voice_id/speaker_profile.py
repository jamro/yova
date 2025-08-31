#!/usr/bin/env python3
"""
Speaker Profile Management

This module provides the SpeakerProfile class for managing individual speaker profiles,
including embeddings storage, sample operations, and profile statistics.
"""

import numpy as np
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SpeakerProfile:
    """Manages individual speaker profile data and operations"""
    
    def __init__(self, speaker_id: str):
        """
        Initialize a speaker profile
        
        Args:
            speaker_id: Unique identifier for the speaker
        """
        self.speaker_id = speaker_id
        self.embeddings: List[np.ndarray] = []
        self.metadata: Dict[str, Any] = {
            'created_at': None,  # Could be enhanced with timestamps
            'last_updated': None,
            'total_samples': 0
        }
    
    def add_embedding(self, embedding: np.ndarray) -> bool:
        """
        Add a new embedding to the speaker's profile
        
        Args:
            embedding: Speaker's embedding vector
            
        Returns:
            True if embedding added successfully
        """
        try:
            # Make a copy to avoid external modifications
            embedding_copy = embedding.copy()
            self.embeddings.append(embedding_copy)
            self.metadata['total_samples'] = len(self.embeddings)
            self.metadata['last_updated'] = None  # Could be enhanced with timestamps
            return True
        except Exception as e:
            logger.error(f"Failed to add embedding for speaker {self.speaker_id}: {e}")
            return False
    
    def remove_embedding(self, index: int) -> bool:
        """
        Remove a specific embedding by index
        
        Args:
            index: Index of the embedding to remove
            
        Returns:
            True if embedding removed successfully, False otherwise
        """
        if 0 <= index < len(self.embeddings):
            self.embeddings.pop(index)
            self.metadata['total_samples'] = len(self.embeddings)
            self.metadata['last_updated'] = None  # Could be enhanced with timestamps
            logger.debug(f"Removed embedding {index} from speaker {self.speaker_id}")
            return True
        return False
    
    def clear_all_embeddings(self) -> int:
        """
        Remove all embeddings from the profile
        
        Returns:
            Number of embeddings removed
        """
        removed_count = len(self.embeddings)
        self.embeddings.clear()
        self.metadata['total_samples'] = 0
        self.metadata['last_updated'] = None  # Could be enhanced with timestamps
        logger.debug(f"Cleared all {removed_count} embeddings from speaker {self.speaker_id}")
        return removed_count
    
    def get_embedding(self, index: int = None) -> Optional[np.ndarray]:
        """
        Get a specific embedding or the averaged embedding
        
        Args:
            index: Specific embedding index, or None for averaged embedding
            
        Returns:
            Embedding vector or None if not found
        """
        if not self.embeddings:
            return None
        
        if index is not None:
            if 0 <= index < len(self.embeddings):
                return self.embeddings[index].copy()
            return None
        
        # Return averaged embedding
        return self.get_averaged_embedding()
    
    def get_averaged_embedding(self) -> Optional[np.ndarray]:
        """
        Get the averaged embedding for the speaker
        
        Returns:
            Averaged embedding vector or None if no embeddings
        """
        if not self.embeddings:
            return None
        
        # If only one embedding, return it directly
        if len(self.embeddings) == 1:
            return self.embeddings[0].copy()
        
        # Average multiple embeddings
        avg_embedding = np.mean(self.embeddings, axis=0)
        # Renormalize
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        return avg_embedding
    
    def get_sample_count(self) -> int:
        """
        Get the number of samples for this speaker
        
        Returns:
            Number of samples
        """
        return len(self.embeddings)
    
    def get_embeddings_list(self) -> List[np.ndarray]:
        """
        Get a copy of all embeddings
        
        Returns:
            List of embedding vectors
        """
        return [emb.copy() for emb in self.embeddings]
    
    def get_embeddings_for_storage(self) -> List[np.ndarray]:
        """
        Get embeddings in the format expected by storage layer
        
        Returns:
            List of embedding vectors (copies)
        """
        return self.get_embeddings_list()
    
    def has_embeddings(self) -> bool:
        """
        Check if the profile has any embeddings
        
        Returns:
            True if profile has embeddings, False otherwise
        """
        return len(self.embeddings) > 0
    
    def is_empty(self) -> bool:
        """
        Check if the profile is empty
        
        Returns:
            True if profile has no embeddings, False otherwise
        """
        return len(self.embeddings) == 0
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the profile
        
        Returns:
            Dictionary containing profile summary information
        """
        return {
            'speaker_id': self.speaker_id,
            'sample_count': len(self.embeddings),
            'has_embeddings': self.has_embeddings(),
            'metadata': self.metadata.copy()
        }
    
    def validate_embeddings(self) -> bool:
        """
        Validate that all embeddings are valid numpy arrays
        
        Returns:
            True if all embeddings are valid, False otherwise
        """
        if not self.embeddings:
            return True  # Empty profile is valid
        
        try:
            for i, emb in enumerate(self.embeddings):
                if not isinstance(emb, np.ndarray):
                    logger.warning(f"Invalid embedding type at index {i} for speaker {self.speaker_id}")
                    return False
                if emb.size == 0:
                    logger.warning(f"Empty embedding at index {i} for speaker {self.speaker_id}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validating embeddings for speaker {self.speaker_id}: {e}")
            return False
    
    def get_embedding_dimensions(self) -> Optional[int]:
        """
        Get the dimension of the embeddings
        
        Returns:
            Embedding dimension or None if no embeddings
        """
        if not self.embeddings:
            return None
        
        try:
            return self.embeddings[0].size
        except (AttributeError, IndexError):
            return None
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embeddings
        
        Returns:
            Dictionary containing embedding statistics
        """
        if not self.embeddings:
            return {
                'count': 0,
                'dimension': None,
                'mean_norm': None,
                'std_norm': None
            }
        
        try:
            norms = [np.linalg.norm(emb) for emb in self.embeddings]
            return {
                'count': len(self.embeddings),
                'dimension': self.embeddings[0].size,
                'mean_norm': np.mean(norms),
                'std_norm': np.std(norms)
            }
        except Exception as e:
            logger.error(f"Error calculating embedding stats for speaker {self.speaker_id}: {e}")
            return {
                'count': len(self.embeddings),
                'dimension': None,
                'mean_norm': None,
                'std_norm': None
            }
