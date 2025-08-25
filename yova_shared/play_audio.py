import os
from pydub import AudioSegment
import asyncio
from pydub.playback import _play_with_simpleaudio as play_playback

async def play_audio(path_to_audio_file, volume_gain=0) -> AudioSegment:
    # Load and play the audio file
    audio = AudioSegment.from_wav(path_to_audio_file)
    # Reduce volume
    audio = audio + volume_gain
    playback = await asyncio.to_thread(play_playback, audio)
    await asyncio.to_thread(playback.wait_done)
    return playback