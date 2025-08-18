import asyncio
import os
from dotenv import load_dotenv
from yova_core.speech2text import RealtimeTranscriber
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
from yova_core.speech2text.audio_recorder import AudioRecorder
from yova_core.core.logging_utils import setup_logging, get_clean_logger
from yova_core.api import OpenAIConnector
from yova_core.text2speech.speech_handler import SpeechHandler

load_dotenv()


async def main():
    print("Starting YOVA - Your Own Voice Assistant...")

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

    # Create speech handler
    speech_handler = SpeechHandler(logger, api_key)

    # Create API connector
    api_connector = OpenAIConnector(logger)
    async def onMessageChunk(chunk):
        #print(chunk['text'], end="", flush=True)
        await speech_handler.process_chunk(chunk['id'], chunk['text'])

    async def onMessageCompleted(chunk):
        #print("\n")
        await speech_handler.process_complete(chunk['id'], chunk['text'])

    api_connector.add_event_listener("message_chunk", onMessageChunk)
    api_connector.add_event_listener("message_completed", onMessageCompleted)
    await api_connector.configure({"api_key": api_key})
    await api_connector.connect()

    # Create transcriber with the provider and audio recorder
    async def onTranscriptionCompleted(data):
        await audio_recorder.stop_recording()
        await transcriber.transcription_provider.stop_listening()
        await transcriber.transcription_provider.close()
        print("PROMPT: ", data['transcript'])
        await api_connector.send_message(data['transcript'])

    async def onTranscriptionError(data):
        print("!!!", data['error'])

    transcriber = RealtimeTranscriber(transcription_provider, audio_recorder, logger=logger)
    transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)
    transcriber.add_event_listener("transcription_error", onTranscriptionError)

    # start session manager ------------------------------------------------------------
    await transcriber.start_realtime_transcription()
    await audio_recorder.start_recording()
    await speech_handler.start()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await speech_handler.stop()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run() # Test comment
