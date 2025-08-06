"""Main application module for Voice Command Station."""

import asyncio
import os
import sys
from typing import Optional
from dotenv import load_dotenv
from voice_command_station.speech2text import RealtimeTranscriber, AudioSessionManager
from voice_command_station.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
from voice_command_station.speech2text.audio_recorder import AudioRecorder
from voice_command_station.core.logging_utils import setup_logging, get_clean_logger

load_dotenv()

async def onTranscriptionCompleted(data):
    print(">>>", data['transcript'])

async def main():
    print("Starting Voice Command Station...")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    # Create transcription provider
    transcription_provider = OpenAiTranscriptionProvider(api_key, logger)
    
    # Create audio recorder
    audio_recorder = AudioRecorder(logger)
    
    # Create transcriber with the provider and audio recorder
    transcriber = RealtimeTranscriber(transcription_provider, audio_recorder, logger=logger)
    transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)

    # Create audio session manager to handle the recording lifecycle
    session_manager = AudioSessionManager(transcriber, audio_recorder, logger=logger)

    try:
        await session_manager.start_session()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session_manager.cleanup()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run() 