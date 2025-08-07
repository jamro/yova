"""
Core package for the voice command station.
"""

from .event_emitter import EventEmitter
from .event_source import EventSource

__all__ = ['EventEmitter', 'EventSource']
