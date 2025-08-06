"""Main application module for Voice Command Station."""

import asyncio
import os
import sys
from typing import Optional
from dotenv import load_dotenv
from voice_command_station.speech2text import RealtimeTranscriber
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
    root_logger = setup_logging()
    logger = get_clean_logger("main", root_logger)

    transcriber = RealtimeTranscriber(api_key, logger=logger)
    transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)


    try:
        await transcriber.start_realtime_transcription()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        transcriber.cleanup()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run() 