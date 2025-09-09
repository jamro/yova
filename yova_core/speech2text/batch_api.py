from yova_core.speech2text.transcription_api import TranscriptionApi
from yova_shared import get_clean_logger
from typing import Optional
from openai import OpenAI
import io
import wave
import struct
from yova_core.cost_tracker import CostTracker

class BatchApi(TranscriptionApi):
    def __init__(self, logger, api_key, model="gpt-4o-transcribe", prompt="", cost_tracker=None):
        self.logger = get_clean_logger("batch_api", logger)
        self.buffer = []
        self.error = None
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.prompt = prompt
        self.cost_tracker = cost_tracker or CostTracker(logger)

    @property
    def is_connected(self) -> bool:
        return True  # Batch API doesn't need persistent connection

    async def connect(self) -> bool:
        return True  # Batch API doesn't need connection setup

    async def disconnect(self) -> None:
        pass  # Batch API doesn't need cleanup

    async def send_audio_chunk(self, audio_chunk: bytes, exception_on_error: bool = True) -> bool:
        self.buffer.append(audio_chunk)
        return True
    
    async def clear_audio_buffer(self, exception_on_error: bool = True) -> bool:
        self.buffer = []
        return True

    async def commit_audio_buffer(self, exception_on_error: bool = True) -> str:
        if len(self.buffer) == 0:
            return ''

        try:
            audio_bytes = b''.join(self.buffer)
            
            # Create a proper WAV file format
            wav_buffer = io.BytesIO()
            
            # WAV file parameters (assuming 16kHz, 16-bit, mono)
            sample_rate = 16000
            num_channels = 1
            sample_width = 2  # 16-bit = 2 bytes
            
            # Calculate number of samples
            num_samples = len(audio_bytes) // sample_width
            
            # Write WAV header
            wav_buffer.write(b'RIFF')
            wav_buffer.write(struct.pack('<I', 36 + num_samples * sample_width))  # File size - 8
            wav_buffer.write(b'WAVE')
            wav_buffer.write(b'fmt ')
            wav_buffer.write(struct.pack('<I', 16))  # Format chunk size
            wav_buffer.write(struct.pack('<H', 1))   # Audio format (PCM)
            wav_buffer.write(struct.pack('<H', num_channels))  # Number of channels
            wav_buffer.write(struct.pack('<I', sample_rate))   # Sample rate
            wav_buffer.write(struct.pack('<I', sample_rate * num_channels * sample_width))  # Byte rate
            wav_buffer.write(struct.pack('<H', num_channels * sample_width))  # Block align
            wav_buffer.write(struct.pack('<H', sample_width * 8))  # Bits per sample
            wav_buffer.write(b'data')
            wav_buffer.write(struct.pack('<I', num_samples * sample_width))  # Data size
            wav_buffer.write(audio_bytes)
            
            # Reset buffer position to beginning
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"
            
            # Use the correct model for transcription
            transcription = self.client.audio.transcriptions.create(
                model=self.model,
                file=wav_buffer,
                prompt=self.prompt
            )
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            if exception_on_error:
                raise e
            
            self.error = str(e)
            return ''

        self.cost_tracker.add_model_cost(
          "core",
          self.model, 
          input_text_tokens=transcription.usage.input_token_details.text_tokens, 
          input_audio_tokens=transcription.usage.input_token_details.audio_tokens, 
          output_text_tokens=transcription.usage.output_tokens
        )

        return transcription.text

    async def query_error(self) -> Optional[str]:
        return self.error

    def get_session_duration(self) -> float:
        return 0.0  # Batch API doesn't track session duration

    def get_inactive_duration(self) -> float:
        return 0.0  # Batch API doesn't track inactivity