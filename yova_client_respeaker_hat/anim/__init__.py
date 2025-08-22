#!/usr/bin/env python3
"""
LED Animation Package

This package provides LED control and animation capabilities for the ReSpeaker HAT.
"""

from .apa102 import APA102, NUM_LEDS
from .animations import (
    BaseAnimation,
    PulseAnimation,
    LightUpAnimation,
    SparkAnimation
)
from .animator import Animator

__all__ = [
    'APA102', 
    'NUM_LEDS', 
    'BaseAnimation',
    'PulseAnimation',
    'LightUpAnimation',
    'SparkAnimation',
    'Animator'
]
__version__ = '1.0.0'
