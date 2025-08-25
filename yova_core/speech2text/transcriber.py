from yova_core.speech2text.realtime_api import RealtimeApi
import asyncio
import pyaudio
import os
from yova_shared import EventEmitter
import uuid
from yova_core.speech2text.audio_buffer import AudioBuffer
from yova_shared import get_clean_logger, play_audio
from yova_core.speech2text.recording_stream import RecordingStream

# Audio recording parameters
CHUNK = 512  # Smaller chunk size for more frequent updates
CHANNELS = 1
RATE = 16000

class Transcriber(EventEmitter):
    def __init__(self, logger, realtime_api: RealtimeApi, audio_buffer: AudioBuffer=None,
                 prerecord_beep="beep1.wav", beep_volume_reduction=18, recording_stream: RecordingStream=None,
                 silence_amplitude_threshold=0.15, min_speech_length=0.5, audio_logs_path=None,
                 pyaudio_instance=None):
        """Initialize the transcriber"""
        super().__init__()
        self.logger = get_clean_logger("transcriber", logger)
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self.realtime_api = realtime_api
        self.listening_task = None
        self.prerecord_beep = prerecord_beep
        self.is_recording = False
        self.beep_volume_reduction = beep_volume_reduction
        self.recording_stream = recording_stream or RecordingStream(
            logger=logger,
            channels=CHANNELS,
            rate=RATE,
            chunk=CHUNK,
            pyaudio_instance=self._pyaudio_instance,
        )
        self.audio_buffer = audio_buffer or AudioBuffer(
            logger=logger, 
            audio_logs_path=audio_logs_path, 
            channels=CHANNELS, 
            sample_rate=RATE, 
            pyaudio_instance=self._pyaudio_instance,
            silence_amplitude_threshold=silence_amplitude_threshold,
            min_speech_length=min_speech_length
        )

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
        self.audio_buffer.start_recording()
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
        self.recording_stream.close()
        self.logger.info("Audio stream closed")
        
        if self.listening_task:
            self.listening_task.cancel()
            self.listening_task = None
        else:
            self.logger.warning("No listening task to stop")

        await self.audio_buffer.save_to_file()

        try:
            if self.audio_buffer.is_empty():
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

        try:
            self.logger.info("Clearing audio buffer")
            await self.realtime_api.clear_audio_buffer()
            
            self.logger.info("Creating audio stream")
            start_time = asyncio.get_event_loop().time()
            self.recording_stream.create()
            dt = asyncio.get_event_loop().time() - start_time
            self.logger.info(f"Audio ready after {round(1000*dt)}ms")

            await self.emit_event("audio_recording_started", { "id": str(uuid.uuid4())})

            # Play the prerecord beep
            if self.prerecord_beep:
                beep_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "yova_shared", "assets", self.prerecord_beep
                )
                await play_audio(beep_path, -self.beep_volume_reduction)

            self.is_recording = True

            while self.is_recording:
                chunk = self.recording_stream.read()

                # Store audio chunk for logging if enabled
                self.audio_buffer.add(chunk)

                if self.recording_stream.is_buffer_full():
                    self.logger.warning(f"Audio buffer is full. Data in buffer: {self.recording_stream.get_buffer_length()}")

                await self.realtime_api.send_audio_chunk(chunk)
                error = await self.realtime_api.query_error()
                if error:
                    self.logger.error(f"Error: {error}")
                    break
                await asyncio.sleep(0.02)
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise e