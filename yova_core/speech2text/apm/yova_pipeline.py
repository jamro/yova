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
    def __init__(self, logger, sample_rate=16000, chunk_size=480, dc_removal_cutoff_freq=20.0, high_pass_cutoff_freq=70.0, 
                 declicking=True, noise_supresion_level=2, agc_enabled=True, vad_aggressiveness=2, normalization_enabled=True, 
                 normalization_target_rms_dbfs=-20.0, normalization_peak_limit_dbfs=-3.0, edge_fade_enabled=True):
        super().__init__(logger, "YovaPipeline")
        
        if dc_removal_cutoff_freq is not None:
            self.add_processor(DCRemovalProcessor(
                logger, 
                sample_rate=sample_rate, 
                cutoff_freq=dc_removal_cutoff_freq
            )) 

        if high_pass_cutoff_freq is not None:
            self.add_processor(SpeechHighPassProcessor(
                logger, 
                sample_rate=sample_rate, 
                cutoff_freq=high_pass_cutoff_freq
            )) 

        if declicking:
            self.add_processor(DeclickingProcessor(logger)) 
            
        if noise_supresion_level is not None:
            self.add_processor(NoiseSuppressionProcessor(
                logger, 
                sample_rate=sample_rate, 
                level=noise_supresion_level
            )) 
        
        if agc_enabled:
            self.add_processor(AGCProcessor(
                logger, 
                sample_rate=sample_rate, 
                target_level_dbfs=-18.0, 
                max_gain_db=20.0, 
                min_gain_db=-20.0, 
                attack_time_ms=5.0, 
                release_time_ms=50.0, 
                ratio=4.0
            ))

        self.add_processor(VADProcessor(
            logger, 
            aggressiveness=vad_aggressiveness, 
            sample_rate=sample_rate, 
            chunk_size=chunk_size
        ))

        if normalization_enabled:
            self.add_processor(NormalizationProcessor(
                logger, 
                sample_rate=sample_rate, 
                target_rms_dbfs=normalization_target_rms_dbfs,
                peak_limit_dbfs=normalization_peak_limit_dbfs
            )) 

        if edge_fade_enabled:
            self.add_processor(EdgeFadeProcessor(
                logger, 
                sample_rate=sample_rate
            ))