from yova_core.speech2text.apm import (
    DCRemovalProcessor,
    SpeechHighPassProcessor,
    DeclickingProcessor,
    NoiseSuppressionProcessor,
    AGCProcessor,
    NormalizationProcessor,
    EdgeFadeProcessor,
)
from yova_core.speech2text.apm.vad_processor import VADProcessor
from yova_core.speech2text.apm import AudioPipeline


class YovaPipeline(AudioPipeline):
    def __init__(self, logger):
        super().__init__(logger, "YovaPipeline")
        
        self.add_processor(DCRemovalProcessor(logger, sample_rate=16000, cutoff_freq=20.0)) 
        self.add_processor(SpeechHighPassProcessor(logger, sample_rate=16000, cutoff_freq=70.0)) 
        self.add_processor(DeclickingProcessor(logger)) 
        self.add_processor(NoiseSuppressionProcessor(logger, sample_rate=16000, level=2)) 
        self.add_processor(AGCProcessor(logger, sample_rate=16000, target_level_dbfs=-18.0, max_gain_db=20.0, min_gain_db=-20.0, attack_time_ms=5.0, release_time_ms=50.0, ratio=4.0))
        self.add_processor(VADProcessor(logger, aggressiveness=2, sample_rate=16000, chunk_size=480))
        self.add_processor(NormalizationProcessor(logger, sample_rate=16000, target_rms_dbfs=-20.0, peak_limit_dbfs=-3.0)) 
        self.add_processor(EdgeFadeProcessor(logger, sample_rate=16000))