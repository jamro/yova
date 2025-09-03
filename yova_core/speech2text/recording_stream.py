from yova_shared import get_clean_logger
import pyaudio

class RecordingStream:
    def __init__(self, logger, channels=1, rate=16000, chunk=480, pyaudio_instance=None):
        self.logger = get_clean_logger("recording_stream", logger)
        self._pyaudio_instance = pyaudio_instance or pyaudio.PyAudio()
        self.audio_stream = None
        self.channels = channels
        self.rate = rate
        self.chunk = chunk

    def create(self, **kwargs):
        self.audio_stream = self._pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            **kwargs
        )
        return self.audio_stream
    
    def read(self):
        return self.audio_stream.read(max(self.chunk, self.audio_stream.get_read_available()), exception_on_overflow=False)
    
    def close(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None

    def is_buffer_full(self):
        return self.audio_stream.get_read_available() >= max(1024, self.chunk)
    
    def get_buffer_length(self):
        return self.audio_stream.get_read_available()