from .vad import VAD
from .base_processor import AudioProcessor, AudioPipeline
from .processors import (
    DCRemovalProcessor, SpeechHighPassProcessor, NoiseSuppressionProcessor,
    NormalizationProcessor, DeclickingProcessor, EdgeFadeProcessor
)


__all__ = [
    # Core classes
    "VAD",
    
    # Modular pipeline classes
    "AudioProcessor", "AudioPipeline",
    
    # Individual processors
    "DCRemovalProcessor", "SpeechHighPassProcessor", "NoiseSuppressionProcessor",
    "NormalizationProcessor", "DeclickingProcessor", "EdgeFadeProcessor"
]