"""
Individual audio processing components for modular pipeline
"""
# Import all processors from their individual files
from .dc_removal_processor import DCRemovalProcessor
from .speech_highpass_processor import SpeechHighPassProcessor
from .noise_suppression_processor import NoiseSuppressionProcessor
from .normalization_processor import NormalizationProcessor
from .declicking_processor import DeclickingProcessor
from .edge_fade_processor import EdgeFadeProcessor
from .agc_processor import AGCProcessor

# Re-export all processors for backward compatibility
__all__ = [
    'DCRemovalProcessor',
    'SpeechHighPassProcessor', 
    'NoiseSuppressionProcessor',
    'NormalizationProcessor',
    'DeclickingProcessor',
    'EdgeFadeProcessor',
    'AGCProcessor'
]
