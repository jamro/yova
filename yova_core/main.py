import asyncio
import os
from dotenv import load_dotenv
from yova_core.speech2text import RealtimeTranscriber
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
from yova_shared import setup_logging, get_clean_logger
from yova_core.text2speech.speech_handler import SpeechHandler
from yova_shared.broker import Publisher, Subscriber  

load_dotenv()

async def main():
    print("Starting YOVA - Your Own Voice Assistant...")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    # Create speech handler
    speech_handler = SpeechHandler(logger, api_key)

    # Create transcriber with the provider
    transcriber = RealtimeTranscriber(OpenAiTranscriptionProvider(api_key, logger), logger=logger)

    # Create broker publisher for voice command events
    voice_command_publisher = Publisher()
    await voice_command_publisher.connect()
    
    # Create broker subscriber for voice command events
    voice_command_subscriber = Subscriber()
    await voice_command_subscriber.connect()
    await voice_command_subscriber.subscribe("voice_command_detected")
    
    # Create broker subscriber for voice response events
    voice_response_subscriber = Subscriber()
    await voice_response_subscriber.connect()
    await voice_response_subscriber.subscribe("voice_response")
    
    # Handle voice response events from the broker
    async def onVoiceResponse(topic, data):
        logger.info(f"Received voice response event: {data['type']} for message {data['id']}")
        
        if data['type'] == "chunk":
            # Handle speech chunk
            await speech_handler.process_chunk(data['id'], data['text'])
        elif data['type'] == "completed":
            # Handle speech complete
            await speech_handler.process_complete(data['id'], data['text'])

    # Handle voice command detection events from the broker
    async def onVoiceCommandDetected(topic, data):
        logger.info(f"Received voice command detection event: {data['transcript']}")
        
        # Handle transcription completed logic
        await transcriber.stop_audio_recording()
        print("PROMPT: ", data['transcript'])

    # Start listening for voice command events
    voice_command_listener_task = asyncio.create_task(
        voice_command_subscriber.listen(onVoiceCommandDetected)
    )
    
    # Start listening for voice response events
    voice_response_listener_task = asyncio.create_task(
        voice_response_subscriber.listen(onVoiceResponse)
    )

    async def onTranscriptionCompleted(data):
        # Publish voice command detection event
        try:
            await voice_command_publisher.publish("voice_command_detected", {
                "transcript": data['transcript'],
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Failed to publish voice command detection event: {e}")

    async def onTranscriptionError(data):
        logger.error(f"Transcription error: {data['error']}")


    transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)
    transcriber.add_event_listener("transcription_error", onTranscriptionError)

    # start session manager ------------------------------------------------------------
    await transcriber.start_realtime_transcription()
    await transcriber.start_audio_recording()
    await speech_handler.start()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await speech_handler.stop()
    await voice_command_listener_task
    await voice_response_listener_task
    await voice_command_subscriber.close()
    await voice_response_subscriber.close()
    await voice_command_publisher.close()
    await transcriber.stop_realtime_transcription()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
