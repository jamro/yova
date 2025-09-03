import soundfile as sf
import numpy as np
from yova_shared import get_clean_logger
import logging
import asyncio
import os
import wave
import pyaudio
import time
from yova_core.speech2text.audio_buffer import AudioBuffer
from yova_core.speech2text.apm import YovaPipeline
from yova_core.speech2text.apm import VAD, AudioPipeline, DCRemovalProcessor, SpeechHighPassProcessor, NoiseSuppressionProcessor, NormalizationProcessor, DeclickingProcessor, EdgeFadeProcessor, AGCProcessor
from yova_core.speech2text.recording_stream import RecordingStream
from scipy.signal import resample_poly
logger = get_clean_logger("apm_demo", logging.getLogger())

class FileAudioStream:
    """Simulates RecordingStream but reads from a WAV file chunk by chunk"""
    
    def __init__(self, file_path: str, chunk_size: int = 480, sample_rate: int = 16000):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
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
            
            logger.info(f"Loaded audio file: {self.total_samples} samples at {self.sample_rate}Hz")
            
        except Exception as e:
            logger.error(f"Error loading audio file {self.file_path}: {e}")
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

def record_input_wav(output_path: str, duration_seconds: int = 5):
    """Record audio for specified duration and save as WAV file"""
    logger = get_clean_logger("record_input", logging.getLogger())
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Initialize recording stream
    recording_stream = RecordingStream(logger, channels=1, rate=16000, chunk=480)
    recording_stream.create()
    
    print(f"Recording {duration_seconds} seconds of audio...")
    print("Speak now!")
    
    # Calculate number of chunks needed
    chunk_size = 480
    sample_rate = 16000
    total_chunks = int((duration_seconds * sample_rate) / chunk_size)
    
    audio_data = []
    
    try:
        for i in range(total_chunks):
            chunk = recording_stream.read()
            audio_data.append(chunk)
            
            # Show progress
            progress = (i + 1) / total_chunks * 100
            print(f"\rRecording progress: {progress:.1f}%", end="", flush=True)
        
        print("\nRecording complete!")
        
        # Convert bytes to numpy array
        audio_bytes = b''.join(audio_data)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # Save as WAV file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_bytes)
        
        logger.info(f"Saved recorded audio to {output_path}")
        print(f"Audio saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error during recording: {e}")
        raise
    finally:
        recording_stream.close()

def play_audio_file(file_path: str):
    """Play an audio file using PyAudio"""
    logger = get_clean_logger("play_audio", logging.getLogger())
    
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        print(f"Error: Audio file not found: {file_path}")
        return
    
    try:
        # Open the WAV file
        with wave.open(file_path, 'rb') as wav_file:
            # Get audio parameters
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.getnframes()
            
            print(f"Playing audio file: {file_path}")
            print(f"Duration: {frames / sample_rate:.2f} seconds")
            print(f"Sample rate: {sample_rate} Hz, Channels: {channels}, Sample width: {sample_width} bytes")
            
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            
            # Open audio stream for playback
            stream = p.open(
                format=p.get_format_from_width(sample_width),
                channels=channels,
                rate=sample_rate,
                output=True
            )
            
            # Read and play audio data in chunks
            chunk_size = 1024
            data = wav_file.readframes(chunk_size)
            
            while data:
                stream.write(data)
                data = wav_file.readframes(chunk_size)
            
            # Clean up
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            print("Playback complete!")
            
    except Exception as e:
        logger.error(f"Error playing audio file: {e}")
        print(f"Error playing audio: {e}")



async def main_recording_step(input_file_path):
    while True:
        user_input = input(f"\nDo you want to record a new input1.wav file? (y/n): ").lower().strip()
        if user_input in ['y', 'yes']:
            try:
                record_input_wav(input_file_path, duration_seconds=5)
                break
            except Exception as e:
                print(f"Error recording audio: {e}")
                print("Please check your microphone and try again.")
                continue
        elif user_input in ['n', 'no']:
            # Check if input file exists
            if not os.path.exists(input_file_path):
                print(f"Error: Input file {input_file_path} does not exist.")
                print("Please record a new file or provide an existing input1.wav file.")
                continue
            print(f"Using existing input file: {input_file_path}")
            break
        else:
            print("Please enter 'y' for yes or 'n' for no.")


async def main_processing_step(logger, input_file_path, output_file_path):

    # Initialize VAD with 30ms frames (480 samples at 16kHz), moderate aggressiveness
    vad = VAD(logger, aggressiveness=2, sample_rate=16000, frame_duration_ms=30)
    frame_size = vad.frame_size  # 480 samples for 30ms at 16kHz
    print(f"Frame size: {frame_size}")
    
    # Create speech processing pipeline directly
    speech_pipeline = YovaPipeline(logger)

    # Initialize file stream with VAD-compatible chunk size
    audio_stream = FileAudioStream(input_file_path, chunk_size=frame_size)

    audio_buffer = AudioBuffer(logger, audio_logs_path="tmp/apm/")
    audio_buffer.start_recording()
    
    chunk_count = 0
    speech_chunks = 0
    silence_chunks = 0
    
    # Calculate chunk duration in seconds for percentage calculation
    chunk_duration_seconds = frame_size / 16000.0  # frame_size samples at 16kHz
    
    # Track processing times for statistics
    processing_times = []
    processing_percentages = []
    
    while not audio_stream.is_finished():
        # Start timing for this chunk
        chunk_start_time = time.perf_counter()
        
        audio_chunk = audio_stream.read()
        
        if audio_chunk is None:
            break
        
        # Process audio through speech pipeline
        audio_chunk_clean = speech_pipeline.process_chunk(audio_chunk)
        
        # Process chunk with VAD
        processed_chunk, is_speech = vad.process_audio_chunk(audio_chunk)
        
        # End timing for this chunk
        chunk_end_time = time.perf_counter()
        processing_time = chunk_end_time - chunk_start_time
        
        # Calculate processing time as percentage of chunk duration
        processing_percentage = (processing_time / chunk_duration_seconds) * 100
        
        # Store timing data for statistics
        processing_times.append(processing_time)
        processing_percentages.append(processing_percentage)
        
        # Always buffer processed audio for ASR continuity
        if is_speech:
            speech_chunks += 1
            print(f"Chunk {chunk_count}: SPEECH detected ({len(audio_chunk_clean)} bytes) - Processing: {processing_percentage:.1f}%")
            audio_buffer.add(audio_chunk_clean)
        else:
            silence_chunks += 1
            print(f"Chunk {chunk_count}: silence ({len(audio_chunk_clean)} bytes) - Processing: {processing_percentage:.1f}%")
        

        chunk_count += 1
    
    print(f"Finished processing {chunk_count} chunks")
    print(f"Speech chunks: {speech_chunks}, Silence chunks: {silence_chunks}")
    print(f"Speech ratio: {speech_chunks/chunk_count*100:.1f}%")
    
    # Print processing time statistics
    if processing_times:
        avg_processing_time = np.mean(processing_times)
        avg_processing_percentage = np.mean(processing_percentages)
        max_processing_percentage = np.max(processing_percentages)
        min_processing_percentage = np.min(processing_percentages)
        
        print(f"\n=== Processing Time Statistics ===")
        print(f"Average processing time: {avg_processing_time*1000:.2f}ms")
        print(f"Average processing percentage: {avg_processing_percentage:.1f}% of chunk duration")
        print(f"Min processing percentage: {min_processing_percentage:.1f}%")
        print(f"Max processing percentage: {max_processing_percentage:.1f}%")
        print(f"Real-time factor: {avg_processing_percentage/100:.3f}x")
    
    # Reset pipeline state for next use
    speech_pipeline.reset_all_states()
    
    await audio_buffer.save_to_file(output_file_path)

def main_playback_step(output_file_path):
    # Play the output file
    if output_file_path and os.path.exists(output_file_path):
        print(f"\n=== Playing Processed Audio ===")
        play_audio_file(output_file_path)
    else:
        print("No output file was generated or file not found.")

async def main():
    print("APM Demo - Reading file chunk by chunk with WebRTC VAD and Modular Audio Processing Pipeline")

    logger = logging.getLogger()

    #await main_recording_step("tmp/apm/test.wav")
    await main_processing_step(logger, "tmp/apm/input1.wav", "tmp/apm/output1.wav")
    await main_processing_step(logger, "tmp/apm/input2.wav", "tmp/apm/output2.wav")
    await main_processing_step(logger, "tmp/apm/input3.wav", "tmp/apm/output3.wav")
    await main_processing_step(logger, "tmp/apm/input4.wav", "tmp/apm/output4.wav")
    await main_processing_step(logger, "tmp/apm/input5.wav", "tmp/apm/output5.wav")
    #main_playback_step("tmp/apm/test.wav")

    
if __name__ == "__main__":
    asyncio.run(main())