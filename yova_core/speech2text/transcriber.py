from yova_core.speech2text.realtime_api import RealtimeApi
import asyncio
import pyaudio
import os
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio as play_audio
from yova_shared import EventEmitter
import uuid
import numpy as np
from datetime import datetime
import wave

# Audio recording parameters
CHUNK = 512  # Smaller chunk size for more frequent updates
CHANNELS = 1
RATE = 16000

def get_audio_amplitude(audio_chunk):
    if not audio_chunk:
        return None

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0
    
    max_amplitude = np.max(np.abs(audio_array))
    return max_amplitude / 32768.0

def get_audio_len(audio_chunk): # returns length in seconds
    if not audio_chunk:
        return 0

    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    if len(audio_array) == 0:
        return 0

    seconds = len(audio_array) / (RATE * CHANNELS)
    return seconds

class Transcriber(EventEmitter):
    def __init__(self, logger, realtime_api: RealtimeApi, pyaudio_instance=None, 
                 stream_factory=None, prerecord_beep="beep1.wav", beep_volume_reduction=18, 
                 silence_amplitude_threshold=0.15, min_speech_length=0.5, audio_logs_path=None):
        """Initialize the transcriber"""
        super().__init__()
        self.logger = logger
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self._stream_factory = stream_factory or self._create_default_stream
        self.realtime_api = realtime_api
        self.listening_task = None
        self.audio_stream = None
        self.prerecord_beep = prerecord_beep
        self.is_recording = False
        self.beep_volume_reduction = beep_volume_reduction
        self.silence_amplitude_threshold = silence_amplitude_threshold
        self.is_buffer_empty = True
        self.buffer_length = 0
        self.min_speech_length = min_speech_length
        self.audio_logs_path = audio_logs_path
        self.recording_start_time = None
        self.audio_chunks = []

    async def initialize(self):
        """Initialize the transcriber"""
        await self.realtime_api.connect()

    async def cleanup(self):
        """Cleanup the transcriber"""
        await self.realtime_api.disconnect()
        self.is_recording = False
        if self.listening_task:
            self.listening_task.cancel()
            self.listening_task = None

    async def start_listening(self):
        """Start listening for audio and transcribe it"""
        self.logger.info("Starting listening")
        if self.audio_logs_path:
            self.recording_start_time = datetime.now()
            self.audio_chunks = []
            self.logger.info(f"Audio logging enabled. Will save to: {self.audio_logs_path}")
        self.listening_task = asyncio.create_task(self._listen_and_transcribe())


    async def stop_listening(self):
        result = await self._stop_listening()
        await self.emit_event("transcription_completed", {
            "id": str(uuid.uuid4()),
            "transcript": result,
            "timestamp": asyncio.get_event_loop().time()
        })
        return result

    async def _stop_listening(self):
        """Stop listening for audio and transcribe it"""
        self.logger.info("Stopping listening")
        self.is_recording = False

        # Properly close the audio stream first
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
            self.logger.info("Audio stream closed")
        
        if self.listening_task:
            self.listening_task.cancel()
            self.listening_task = None
        else:
            self.logger.warning("No listening task to stop")

        if self.audio_logs_path and self.audio_chunks and not self.is_buffer_empty and self.buffer_length > self.min_speech_length:
            await self._save_audio_file()

        try:
            if self.is_buffer_empty or self.buffer_length < self.min_speech_length:
                self.logger.info("No audio to transcribe, returning empty string")
                return ''
            else:
                text = await self.realtime_api.commit_audio_buffer()
                self.logger.info(f"Transcription: {text}")
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return ''
        
        return text
    
    async def _listen_and_transcribe(self):
        """Start listening for audio and transcribe it"""

        self.logger.info("Clearing audio buffer")
        await self.realtime_api.clear_audio_buffer()
        self.is_buffer_empty = True
        self.buffer_length = 0
        
        self.logger.info("Creating audio stream")
        start_time = asyncio.get_event_loop().time()
        self.audio_stream = self._stream_factory(self._pyaudio_instance)
        dt = asyncio.get_event_loop().time() - start_time
        self.logger.info(f"Audio ready after {round(1000*dt)}ms")

        await self.emit_event("audio_recording_started", {
            "id": str(uuid.uuid4()),
        })
        await self._play_beep()
        self.is_recording = True

        while self.is_recording:
            chunk = self.audio_stream.read(max(CHUNK, self.audio_stream.get_read_available()), exception_on_overflow=False)

            # Store audio chunk for logging if enabled
            if self.audio_logs_path:
                self.audio_chunks.append(chunk)

            amplitude = get_audio_amplitude(chunk)
            # suppress speech detection if buffer is short to avoid detection of pre-beep silence
            if amplitude > self.silence_amplitude_threshold and self.is_buffer_empty and self.buffer_length > self.min_speech_length:
                self.logger.info("Speech detected")
                self.is_buffer_empty = False

            self.buffer_length += get_audio_len(chunk)
            
            if self.audio_stream.get_read_available() >= 1024:
                self.logger.warning(f"Audio buffer is full. Data in buffer: {self.audio_stream.get_read_available()}")

            await self.realtime_api.send_audio_chunk(chunk)
            error = await self.realtime_api.query_error()
            if error:
                self.logger.error(f"Error: {error}")
                break
            await asyncio.sleep(0.02)
      
    def _create_default_stream(self, pyaudio_instance, **kwargs):
        """Default factory method for creating audio streams"""
        return pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            **kwargs
        )
    
    async def _play_beep(self):
        """Play the beep sound file"""
        if not self.prerecord_beep:
            return
        try:
            # Get the path to the beep file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            beep_path = os.path.join(current_dir, "..", "..", "yova_shared", "assets", self.prerecord_beep)
            
            # Load and play the audio file
            audio = AudioSegment.from_wav(beep_path)
            # Reduce volume
            audio = audio - self.beep_volume_reduction
            playback = await asyncio.to_thread(play_audio, audio)
            await asyncio.to_thread(playback.wait_done)
            
            self.logger.debug("Beep sound played successfully")
        except Exception as e:
            self.logger.warning(f"Could not play beep sound: {e}")

    async def _save_audio_file(self):
        """Save the recorded audio to a file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.audio_logs_path, exist_ok=True)
            
            # Generate filename based on recording start time
            timestamp_str = self.recording_start_time.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove microseconds, keep milliseconds
            filename = f"audio_{timestamp_str}.wav"
            filepath = os.path.join(self.audio_logs_path, filename)
            
            # Save as WAV file
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(self._pyaudio_instance.get_sample_size(pyaudio.paInt16))
                wav_file.setframerate(RATE)
                wav_file.writeframes(b''.join(self.audio_chunks))
            
            self.logger.info(f"Audio saved to: {filepath}")
            
            # Clear chunks to free memory
            self.audio_chunks.clear()
            
        except Exception as e:
            self.logger.error(f"Error saving audio file: {e}")