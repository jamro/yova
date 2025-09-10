"""
Main entry point for YOVA API OpenAI connector
"""

import asyncio
from yova_api_openai.openai_connector import OpenAIConnector
from yova_shared import setup_logging, get_clean_logger
from yova_shared.broker import Publisher, Subscriber
from yova_shared import get_config

async def main():
    """Async main function for the YOVA API OpenAI service"""

    api_key = get_config("open_ai.api_key")

    if not api_key or len(api_key) < 20:
        raise ValueError("open_ai.api_key is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    api_connector = OpenAIConnector(logger)
    
    # Create broker publisher for voice command events
    publisher = Publisher()
    await publisher.connect()

    # Create broker subscriber for voice command events
    subscriber = Subscriber()
    await subscriber.connect()
    await subscriber.subscribe("yova.api.asr.result")

    async def onMessageChunk(chunk):
        # Emit voice response chunk event
        try:
            await publisher.publish("api_connector_openai", "yova.api.tts.chunk", {
                "id": chunk['id'],
                "content": chunk['text'],
                "priority_score": chunk['priority_score']
            })
        except Exception as e:
            logger.error(f"Failed to publish voice response chunk event: {e}")

    async def onMessageCompleted(full_response):
        # Emit voice response completed event
        try:
            await publisher.publish("api_connector_openai", "yova.api.tts.complete", {
                "id": full_response['id'],
                "content": full_response['text']
            })
        except Exception as e:
            logger.error(f"Failed to publish voice response completed event: {e}")

    async def onProcessingStarted(data):
        await publisher.publish("api_connector_openai", "yova.api.thinking.start", {
            "id": data['id']
        })
        
    async def onProcessingCompleted(data):
        await publisher.publish("api_connector_openai", "yova.api.thinking.stop", {
            "id": data['id']
        })  

    async def onTokenUsage(data):
        await publisher.publish("api_connector_openai", "yova.api.usage.occur", {
            "cost": data['cost'],
            "extra_data": {
                "model": data['model']
            }
        })

    api_connector.add_event_listener("message_chunk", onMessageChunk)
    api_connector.add_event_listener("message_completed", onMessageCompleted)
    api_connector.add_event_listener("processing_started", onProcessingStarted)
    api_connector.add_event_listener("processing_completed", onProcessingCompleted)
    api_connector.add_event_listener("token_usage", onTokenUsage)

    await api_connector.configure({"api_key": api_key})
    await api_connector.connect()

    # Handle voice command detection events from the broker
    async def onVoiceCommandDetected(topic, message):
        data = message["data"]

        if data['voice_id'] and data['voice_id']['user_id']:
            prompt = f"""My name is {data['voice_id']['user_id']}. 
            Respond to prompt below using the same language and mentioning my name if suitable:

            Prompt: {data['transcript']}
            """
        else:
            prompt = data['transcript']

        logger.info(f"Received voice command detection event: {data['transcript']}")
        
        # Handle transcription completed logic
        await api_connector.send_message(prompt)

    # Start listening for voice command events
    voice_command_listener_task = asyncio.create_task(
        subscriber.listen(onVoiceCommandDetected)
    )

    await asyncio.get_event_loop().run_in_executor(None, input)

    # clean up
    await publisher.close()
    await subscriber.close()
    await api_connector.close()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
