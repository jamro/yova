from yova_core.speech2text.realtime_api import RealtimeApi
import asyncio
import pyaudio
import os
from yova_shared import EventEmitter
import uuid
from yova_core.speech2text.audio_buffer import AudioBuffer
from yova_shared import get_clean_logger, play_audio
from yova_core.speech2text.recording_stream import RecordingStream
from yova_core.voice_id.voice_id_manager import VoiceIdManager
import numpy as np
import traceback

# Audio recording parameters
CHUNK = 512  # Smaller chunk size for more frequent updates
CHANNELS = 1
RATE = 16000

# Default watchdog parameters
DEFAULT_MAX_SESSION_DURATION = 900  # 15 minutes in seconds
DEFAULT_MAX_INACTIVE_DURATION = 300  # 5 minutes in seconds
DEFAULT_WATCHDOG_CHECK_INTERVAL = 30  # Check every 30 seconds

class Transcriber(EventEmitter):
    def __init__(self, logger, realtime_api: RealtimeApi, voice_id_manager: VoiceIdManager, audio_buffer: AudioBuffer=None,
                 prerecord_beep="beep1.wav", beep_volume_reduction=18, recording_stream: RecordingStream=None,
                 silence_amplitude_threshold=0.15, min_speech_length=0.5, audio_logs_path=None,
                 pyaudio_instance=None, exit_on_error=False,
                 max_session_duration=DEFAULT_MAX_SESSION_DURATION,
                 max_inactive_duration=DEFAULT_MAX_INACTIVE_DURATION,
                 watchdog_check_interval=DEFAULT_WATCHDOG_CHECK_INTERVAL):
        """Initialize the transcriber"""
        super().__init__()
        self.logger = get_clean_logger("transcriber", logger)
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self.realtime_api = realtime_api
        self.voice_id_manager = voice_id_manager
        self.voice_id_result = None
        self.logger.info(f"Voice ID manager is {'enabled' if self.voice_id_manager else 'disabled'}")
        self.voice_id_task = None
        self.listening_task = None
        self.watchdog_task = None
        self.prerecord_beep = prerecord_beep
        self.is_recording = False
        self.exit_on_error = exit_on_error # usfefull when running with supervisor and auto restart turned on
        self.beep_volume_reduction = beep_volume_reduction
        
        # Watchdog configuration
        self.max_session_duration = max_session_duration
        self.max_inactive_duration = max_inactive_duration
        self.watchdog_check_interval = watchdog_check_interval
        
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
        # Start watchdog immediately to monitor the connection
        self.watchdog_task = asyncio.create_task(self._watchdog_monitor())

    async def cleanup(self):
        """Cleanup the transcriber"""
        await self.realtime_api.disconnect()
        self.is_recording = False
        if self.listening_task:
            self.listening_task.cancel()
            self.listening_task = None
        if self.watchdog_task:
            self.watchdog_task.cancel()
            self.watchdog_task = None

    async def start_listening(self):
        """Start listening for audio and transcribe it"""
        self.logger.info("Starting listening")
        self.audio_buffer.start_recording()
        self.listening_task = asyncio.create_task(self._listen_and_transcribe())

    async def stop_listening(self):
        result = await self._stop_listening()
        if self.voice_id_task:
            await self.voice_id_task
            self.voice_id_task = None
        await self.emit_event("transcription_completed", {
            "id": str(uuid.uuid4()),
            "transcript": result,
            "voice_id": self.voice_id_result
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

        if self.voice_id_task:
            self.voice_id_task.cancel()
            self.voice_id_task = None
        
        await self.audio_buffer.save_to_file()

        self.voice_id_task = asyncio.create_task(self.identify_user(self.audio_buffer.buffer))

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
    
    async def identify_user(self, audio_chunks):   
        if not self.voice_id_manager:
            self.voice_id_result = None
            return
        try:
            self.logger.info(f"Identifying user...")
            self.voice_id_result = None

            if audio_chunks is None or len(audio_chunks) == 0:
                self.logger.warning("No audio provided for voice identification")
                return

            joined_bytes = b"".join(audio_chunks)
            pcm16_audio = np.frombuffer(joined_bytes, dtype=np.int16)

            self.voice_id_result = self.voice_id_manager.identify_speaker(pcm16_audio)
            self.logger.info(f"Voice ID identification completed: {self.voice_id_result['user_id']} confidence: {self.voice_id_result['confidence_level']}")
        except Exception as e:
            self.logger.error(f"Error identifying user: {e}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            # Do not re-raise inside background task

        self.voice_id_task = None
    
    async def _watchdog_monitor(self):
        """Monitor the realtime API connection and reconnect if needed"""
        self.logger.info(f"Watchdog started - max session: {self.max_session_duration}s, max inactive: {self.max_inactive_duration}s")
        
        while True:  # Run indefinitely until cancelled
            try:
                await asyncio.sleep(self.watchdog_check_interval)
                
                if not self.realtime_api.is_connected:
                    self.logger.warning("Realtime API not connected, attempting to reconnect...")
                    success = await self._reconnect_realtime_api()
                    if not success and self.exit_on_error:
                        self.logger.error("Reconnection failed and exit_on_error is True - exiting process")
                        os._exit(1)
                    continue
                
                session_duration = self.realtime_api.get_session_duration()
                inactive_duration = self.realtime_api.get_inactive_duration()
                
                self.logger.debug(f"Watchdog check - Session: {session_duration:.1f}s, Inactive: {inactive_duration:.1f}s")
                
                # Only reconnect if NOT currently listening AND thresholds are exceeded
                if (not self.is_recording and 
                    session_duration > self.max_session_duration and 
                    inactive_duration > self.max_inactive_duration):
                    self.logger.warning(f"Watchdog triggered reconnection - Session: {session_duration:.1f}s, Inactive: {inactive_duration:.1f}s")
                    success = await self._reconnect_realtime_api()
                    if not success and self.exit_on_error:
                        self.logger.error("Reconnection failed and exit_on_error is True - exiting process")
                        os._exit(1)
                    
            except asyncio.CancelledError:
                self.logger.info("Watchdog task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Watchdog error: {e}")
                if self.exit_on_error:
                    self.logger.error("Exiting process due to watchdog error")
                    os._exit(1)
                await asyncio.sleep(self.watchdog_check_interval)
    
    async def _reconnect_realtime_api(self):
        """Reconnect the realtime API"""
        try:
            self.logger.info("Disconnecting realtime API for reconnection...")
            await self.realtime_api.disconnect()
            
            self.logger.info("Reconnecting realtime API...")
            await self.realtime_api.connect()
            
            if self.realtime_api.is_connected:
                self.logger.info("Realtime API reconnected successfully")
                # Clear audio buffer after reconnection
                await self.realtime_api.clear_audio_buffer()
                return True
            else:
                self.logger.error("Failed to reconnect realtime API")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during reconnection: {e}")
            if self.exit_on_error:
                self.logger.error("Exiting process due to reconnection error")
                os._exit(1)
            return False
    
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
            if self.exit_on_error:
                # exit process immediately with error code
                self.logger.error("Exiting process due to error")
                os._exit(1)
            raise e