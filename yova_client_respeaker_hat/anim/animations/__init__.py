#!/usr/bin/env python3
"""
LED Animation Classes Package

This subpackage contains all the individual animation implementations.
"""

from .base_animation import BaseAnimation
from .pulse_animation import PulseAnimation
from .light_up_animation import LightUpAnimation
from .spark_animation import SparkAnimation

__all__ = [
    'BaseAnimation',
    'PulseAnimation',
    'LightUpAnimation',
    'SparkAnimation',
]
