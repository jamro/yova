"""
Main entry point for YOVA API OpenAI connector
"""

import asyncio
from yova_api_openai.openai_connector import OpenAIConnector
from yova_shared import setup_logging, get_clean_logger
from yova_shared.broker import Publisher, Subscriber
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    """Async main function for the YOVA API OpenAI service"""

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    api_connector = OpenAIConnector(logger)
    
    # Create broker publisher for voice command events
    voice_response_publisher = Publisher()
    await voice_response_publisher.connect()

    # Create broker subscriber for voice command events
    voice_command_subscriber = Subscriber()
    await voice_command_subscriber.connect()
    await voice_command_subscriber.subscribe("voice_command_detected")

    async def onMessageChunk(chunk):
        # Emit voice response chunk event
        try:
            await voice_response_publisher.publish("voice_response", {
                "type": "chunk",
                "id": chunk['id'],
                "text": chunk['text'],
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Failed to publish voice response chunk event: {e}")

    async def onMessageCompleted(full_response):
        # Emit voice response completed event
        try:
            await voice_response_publisher.publish("voice_response", {
                "type": "completed",
                "id": full_response['id'],
                "text": full_response['text'],
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Failed to publish voice response completed event: {e}")

    api_connector.add_event_listener("message_chunk", onMessageChunk)
    api_connector.add_event_listener("message_completed", onMessageCompleted)
    await api_connector.configure({"api_key": api_key})
    await api_connector.connect()

    # Handle voice command detection events from the broker
    async def onVoiceCommandDetected(topic, data):
        logger.info(f"Received voice command detection event: {data['transcript']}")
        
        # Handle transcription completed logic
        await api_connector.send_message(data['transcript'])

    # Start listening for voice command events
    voice_command_listener_task = asyncio.create_task(
        voice_command_subscriber.listen(onVoiceCommandDetected)
    )

    await asyncio.get_event_loop().run_in_executor(None, input)

    # clean up
    await voice_response_publisher.close()
    await voice_command_subscriber.close()
    await api_connector.close()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
