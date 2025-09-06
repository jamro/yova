# poetry run python tests/asr/asr_test.py
import asyncio
import json
import os
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly
from yova_core.speech2text.apm import AudioPipeline
import logging
from yova_shared import get_clean_logger, get_config
from yova_core.speech2text.audio_buffer import AudioBuffer
from yova_core.speech2text.realtime_api import RealtimeApi
from jiwer import wer, cer
from datetime import datetime
from openai import OpenAI
from yova_core.speech2text.apm import YovaPipeline

TEST_DATA_FILE = "tests/asr/test_data/test_data.json"


class FileAudioStream:
    """Simulates RecordingStream but reads from a WAV file chunk by chunk"""
    
    def __init__(self, file_path: str, chunk_size: int = 480, sample_rate: int = 16000, logger: logging.Logger = None):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.logger = logger
        self.audio_data = None
        self.current_position = 0
        self.total_samples = 0
        self._load_and_prepare_audio()
    
    def _load_and_prepare_audio(self):
        """Load and prepare the audio file for chunk-by-chunk reading"""
        try:
            # Load audio file
            audio, sr = sf.read(self.file_path)
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # Resample to 16kHz if necessary
            if sr != self.sample_rate:
                # Polyphase resampling for better quality
                # Compute integer up/down for resample_poly
                from math import gcd
                g = gcd(int(self.sample_rate), int(sr))
                up = int(self.sample_rate // g)
                down = int(sr // g)
                audio = resample_poly(audio, up, down)
            
            # Convert to PCM 16-bit format (int16)
            if audio.dtype != np.int16:
                # Convert from float32 [-1, 1] to int16 [-32768, 32767]
                if audio.dtype == np.float32 or audio.dtype == np.float64:
                    # Ensure audio is in [-1, 1] range first
                    if np.max(np.abs(audio)) > 1.0:
                        audio = audio / np.max(np.abs(audio))
                    audio = (audio * 32768).astype(np.int16)
                else:
                    # For other integer types, convert directly
                    audio = audio.astype(np.int16)
            
            self.audio_data = audio
            self.total_samples = len(audio)
            self.current_position = 0
            
            self.logger.info(f"Loaded audio file: {self.total_samples} samples at {self.sample_rate}Hz")
            
        except Exception as e:
            self.logger.error(f"Error loading audio file {self.file_path}: {e}")
            raise
    
    def read(self):
        """Read next chunk of audio data, similar to RecordingStream.read()"""
        if self.current_position >= self.total_samples:
            return None  # End of file
        
        # Calculate how many samples to read
        samples_to_read = min(self.chunk_size, self.total_samples - self.current_position)
        
        # Extract chunk
        chunk = self.audio_data[self.current_position:self.current_position + samples_to_read]
        self.current_position += samples_to_read
        
        # Convert to bytes (same format as PyAudio returns)
        audio_bytes = chunk.tobytes()
        
        return audio_bytes
    
    def get_read_available(self):
        """Simulate PyAudio's get_read_available() method"""
        return min(self.chunk_size, self.total_samples - self.current_position)
    
    def is_buffer_full(self):
        """Simulate RecordingStream's is_buffer_full() method"""
        return self.get_read_available() >= max(1024, self.chunk_size)
    
    def get_buffer_length(self):
        """Simulate RecordingStream's get_buffer_length() method"""
        return self.get_read_available()
    
    def reset(self):
        """Reset to beginning of file"""
        self.current_position = 0
    
    def is_finished(self):
        """Check if we've reached the end of the file"""
        return self.current_position >= self.total_samples


async def transcribe_no_streaming(logger, file_path, transcript, realtime_api):
    client = OpenAI(api_key=realtime_api.api_key)
    audio_file = open(file_path, "rb")


    start_time = asyncio.get_event_loop().time()
    transcription = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file
    )
    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time

    return {
      "text": transcription.text,
      "processing_time": processing_time
    }
    

async def transcribe(logger, file_path, transcript, realtime_api):
    frame_size = 480
    
    # Create speech processing pipeline directly
    speech_pipeline = YovaPipeline(
        logger, 
        high_pass_cutoff_freq=get_config("speech2text.preprocessing.high_pass_cutoff_freq") or None, 
        declicking=get_config("speech2text.preprocessing.declicking"), 
        noise_supresion_level=get_config("speech2text.preprocessing.noise_supresion_level") or None, 
        agc_enabled=get_config("speech2text.preprocessing.agc_enabled"), 
        vad_aggressiveness=get_config("speech2text.preprocessing.vad_aggressiveness") or None, 
        normalization_enabled=get_config("speech2text.preprocessing.normalization_enabled"), 
        normalization_target_rms_dbfs=get_config("speech2text.preprocessing.normalization_target_rms_dbfs"), 
        normalization_peak_limit_dbfs=get_config("speech2text.preprocessing.normalization_peak_limit_dbfs"), 
        edge_fade_enabled=get_config("speech2text.preprocessing.edge_fade_enabled")
    )

    #print(f"Speech pipeline: {speech_pipeline.get_pipeline_info()}")


    audio_stream = FileAudioStream(file_path, chunk_size=frame_size, logger=logger)
    
    # Calculate chunk duration in seconds for percentage calculation
    chunk_duration_seconds = frame_size / 16000.0  # frame_size samples at 16kHz
    
    # Track processing times for statistics
    processing_times = []
    processing_percentages = []

    await realtime_api.clear_audio_buffer()

    while not audio_stream.is_finished():
        audio_chunk = audio_stream.read()

        if audio_chunk is None:
            break
        
        audio_chunk_clean = speech_pipeline.process_chunk(audio_chunk)

        if audio_chunk_clean is None:
            continue

        await realtime_api.send_audio_chunk(audio_chunk_clean)
        error = await realtime_api.query_error()
        if error:
            logger.error(f"Error: {error}")
            break
    
    start_time = asyncio.get_event_loop().time()
    text = await realtime_api.commit_audio_buffer()
    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time
    return {
      "text": text,
      "processing_time": processing_time
    }


async def test_asr(logger, file_path, transcript, realtime_api):

    reference = []
    hypothesis = []
    processing_times = []

    print(f"Text: {transcript}", end="", flush=True)

    # repreat 3 times
    for i in range(3):
        print(".", end="", flush=True)
        reference.append(transcript)
        result = await transcribe(logger, file_path, transcript, realtime_api)
        text = result["text"]
        processing_time = result["processing_time"]
        hypothesis.append(text)
        processing_times.append(processing_time)

    wer_score = wer(reference, hypothesis)
    cer_score = cer(reference, hypothesis)

    print(f"\r[WER: {wer_score:.2f}, CER: {cer_score:.2f}] > {transcript}")

    return {
      "wer": wer_score,
      "cer": cer_score,
      "reference": reference,
      "hypothesis": hypothesis,
      "processing_times": processing_times
    }
        

async def main():
    print("ASR Test")

    logger = logging.getLogger()

    api_key = get_config("open_ai.api_key")
    realtime_api = RealtimeApi(
                api_key, 
                logger,
                model=get_config("speech2text.model"),
                language=get_config("speech2text.language"),
                noise_reduction=get_config("speech2text.noise_reduction"),
                instructions=get_config("speech2text.instructions"),
            )

    await realtime_api.connect()

    with open(TEST_DATA_FILE, "r") as f:
        test_data = json.load(f)

    # folder of TEST_DATA_FILE
    base_folder = os.path.dirname(TEST_DATA_FILE)

    reference = []
    hypothesis = []
    processing_times = []

    for item in test_data:
        file_path = os.path.join(base_folder, item["file"])
        result = await test_asr(logger, file_path, item["transcript"], realtime_api)
        reference.extend(result["reference"])
        hypothesis.extend(result["hypothesis"])
        processing_times.extend(result["processing_times"])

    await realtime_api.disconnect()

    # report
    report_data = {
      "name": "Test Results",
      "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    wer_score = wer(reference, hypothesis)
    cer_score = cer(reference, hypothesis)
    report_data["wer"] = wer_score
    report_data["cer"] = cer_score

    avg_processing_time = np.mean(processing_times)
    report_data["avg_processing_time"] = avg_processing_time
    
    test_results = []
    for i in range(len(reference)):
        test_results.append({
            "reference_": reference[i],
            "hypothesis": hypothesis[i],
            "processing_time": processing_times[i]
        })
    report_data["test_results"] = test_results

    report_data["config"] = get_config()

    print(f"="*50)
    print("REPORT")
    print(f"="*50)
    print(f"WER: {wer_score:.2f}, CER: {cer_score:.2f}, Avg Processing Time: {avg_processing_time:.2f}ms")

    # Create reports folder if it doesn't exist
    reports_folder = os.path.join(base_folder, "..", "reports")
    os.makedirs(reports_folder, exist_ok=True)
    
    # Save formatted JSON report
    report_file = os.path.join(reports_folder, "report.json")
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())