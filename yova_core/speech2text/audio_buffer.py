import os
from datetime import datetime
from yova_shared import get_clean_logger
import wave
import pyaudio
import numpy as np
import traceback

def get_audio_amplitude(audio_chunk):
    if not audio_chunk:
        return None

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0
    
    max_amplitude = np.max(np.abs(audio_array))
    return max_amplitude / 32768.0

def get_audio_len(audio_chunk, sample_rate, channels): # returns length in seconds
    if not audio_chunk:
        return 0

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0

    seconds = len(audio_array) / (sample_rate * channels)
    return seconds

class AudioBuffer:
    def __init__(self, logger, audio_logs_path=None, channels=1, sample_rate=16000, 
                 pyaudio_instance=None, silence_amplitude_threshold=0.15, min_speech_length=0.5):
        self.buffer = []
        self.recording_start_time = None
        self.logger = get_clean_logger("audio_buffer", logger)
        self.audio_logs_path = audio_logs_path
        self.channels = channels
        self.sample_rate = sample_rate
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self.silence_amplitude_threshold = silence_amplitude_threshold
        self.min_speech_length = min_speech_length
        self.is_buffer_empty = True
        self.buffer_length = 0

    def start_recording(self):
        if self.audio_logs_path:
            self.logger.info(f"Audio logging enabled. Will save to: {self.audio_logs_path}")
        self.recording_start_time = datetime.now()
        self.clear()
        self.is_buffer_empty = True
        self.buffer_length = 0

    def add(self, audio_chunk):
        self.buffer.append(audio_chunk)

        self.buffer_length += get_audio_len(audio_chunk, self.sample_rate, self.channels)

        amplitude = get_audio_amplitude(audio_chunk)
        # suppress speech detection if buffer is short to avoid detection of pre-beep silence
        if amplitude > self.silence_amplitude_threshold and self.is_buffer_empty and self.buffer_length > self.min_speech_length:
            self.logger.info("Speech detected")
            self.is_buffer_empty = False

    def clear(self):
        self.logger.info(f"Clearing buffer: {self.buffer_length} bytes")
        self.buffer = []


    def is_empty(self):
        return self.is_buffer_empty or self.buffer_length < self.min_speech_length or len(self.buffer) == 0

    async def save_to_file(self):
        """Save the recorded audio to a file"""

        if not self.audio_logs_path or self.is_buffer_empty or self.buffer_length < self.min_speech_length:
            return
        
        if self.recording_start_time is None:
            self.logger.error("Recording start time is not set")
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.audio_logs_path, exist_ok=True)
            
            # Generate filename based on recording start time
            timestamp_str = self.recording_start_time.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove microseconds, keep milliseconds
            filename = f"audio_{timestamp_str}.wav"
            filepath = os.path.join(self.audio_logs_path, filename)
            
            # Save as WAV file
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self._pyaudio_instance.get_sample_size(pyaudio.paInt16))
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(b''.join(self.buffer))
            
            self.logger.info(f"Audio saved to: {filepath}")

            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving audio file: {e}")
            # stack trace
            self.logger.error(traceback.format_exc())