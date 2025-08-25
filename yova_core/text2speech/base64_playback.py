from yova_core.text2speech.playback import Playback
from yova_shared import get_clean_logger
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio as play_audio
from yova_shared import EventEmitter
import base64
import io

# Supported audio formats and their MIME types
SUPPORTED_FORMATS = {
    'wav': 'audio/wav',
    'mp3': 'audio/mpeg',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac',
    'aac': 'audio/aac',
    'm4a': 'audio/mp4',
    'wma': 'audio/x-ms-wma'
}

class Base64Playback(Playback):
    def __init__(self, logger, text):
        super().__init__()
        self.logger = get_clean_logger("base64_playback", logger)
        self.text = text
        self.event_emitter = EventEmitter(logger=logger)

    def add_event_listener(self, event_type: str, listener):
        """Add an event listener for a specific event type."""
        self.event_emitter.add_event_listener(event_type, listener)

    def remove_event_listener(self, event_type: str, listener):
        """Remove an event listener for a specific event type."""
        self.event_emitter.remove_event_listener(event_type, listener)

    def clear_event_listeners(self, event_type: str = None):
        """Clear all event listeners or listeners for a specific event type."""
        self.event_emitter.clear_event_listeners(event_type)

    async def load(self) -> None:
        pass
    
    async def play(self) -> None:
        self.logger.debug(f"Playing data for base64: {self.text[:100]}...")
        data_url = self.text

        try:
            # Parse the data URL to extract MIME type and base64 data
            if not data_url.startswith("data:"):
                raise ValueError("Invalid data URL format. Must start with 'data:'")
            
            # Split the data URL to get MIME type and base64 data
            header, base64_string = data_url.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            
            # Extract format from MIME type
            format_ext = None
            for ext, mime in SUPPORTED_FORMATS.items():
                if mime == mime_type:
                    format_ext = ext
                    break
            
            if format_ext is None:
                raise ValueError(f"Unsupported MIME type: {mime_type}")
            
            # Decode base64 back to binary
            audio_binary = base64.b64decode(base64_string)
            
            # Create a file-like object from the binary data
            audio_file = io.BytesIO(audio_binary)
            
            # Load audio using pydub based on format
            if format_ext == 'wav':
                audio_segment = AudioSegment.from_wav(audio_file)
            elif format_ext == 'mp3':
                audio_segment = AudioSegment.from_mp3(audio_file)
            elif format_ext == 'ogg':
                audio_segment = AudioSegment.from_ogg(audio_file)
            elif format_ext == 'flac':
                audio_segment = AudioSegment.from_file(audio_file, format='flac')
            elif format_ext == 'aac':
                audio_segment = AudioSegment.from_file(audio_file, format='aac')
            elif format_ext == 'm4a':
                audio_segment = AudioSegment.from_file(audio_file, format='mp4')
            elif format_ext == 'wma':
                audio_segment = AudioSegment.from_file(audio_file, format='wma')
            else:
                raise ValueError(f"Unsupported format for playback: {format_ext}")
            
            print(f"Audio loaded: {len(audio_segment)}ms duration, {audio_segment.channels} channels")
            print(f"Format: {format_ext.upper()}, MIME type: {mime_type}")
            
            # Play the audio using simpleaudio
            playback = play_audio(audio_segment)
            
            print("Playing audio...")
            
            # Wait for audio to finish playing
            playback.wait_done()
            
            print("Audio playback finished.")
            
        except Exception as e:
            print(f"Error playing audio: {e}")


    async def stop(self) -> None:
        pass