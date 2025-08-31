#!/usr/bin/env python3
"""
Voice ID Module

This module provides speaker verification and identification capabilities
using ECAPA embeddings and cosine similarity.
"""

from .speaker_verifier import SpeakerVerifier
from .profile_storage import ProfileStorage
from .speaker_profile import SpeakerProfile

__all__ = ['SpeakerVerifier', 'ProfileStorage', 'SpeakerProfile']