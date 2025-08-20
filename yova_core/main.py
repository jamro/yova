import asyncio
import os
from dotenv import load_dotenv
from yova_core.speech2text import RealtimeTranscriber
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
from yova_shared import setup_logging, get_clean_logger
from yova_core.text2speech.speech_handler import SpeechHandler
from yova_shared.broker import Publisher, Subscriber  
from yova_core.state_machine import StateMachine

load_dotenv()

async def main():
    print("Starting YOVA - Your Own Voice Assistant...")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    # Create state machine
    state_machine = StateMachine(
        logger,
        SpeechHandler(logger, api_key),
        RealtimeTranscriber(OpenAiTranscriptionProvider(api_key, logger), logger=logger)
    )
    async def log_state_change(data):
        logger.info(f"State changed: {data['previous_state']} -> {data['new_state']}")
    state_machine.add_event_listener("state_changed", log_state_change)

    # Create broker subscriber for input
    input_subsciber = Subscriber()
    await input_subsciber.connect()
    await input_subsciber.subscribe("input")
    async def onInput(topic, data):
        if data['active'] == True:
            await state_machine.on_input_activated()
        else:
            await state_machine.on_input_deactivated()
    input_listener_task = asyncio.create_task(input_subsciber.listen(onInput))

    # Create broker publisher for voice command events
    voice_command_publisher = Publisher()
    await voice_command_publisher.connect()

    # Create broker subscriber for voice response events
    voice_response_subscriber = Subscriber()
    await voice_response_subscriber.connect()
    await voice_response_subscriber.subscribe("voice_response")
    async def onVoiceResponse(topic, data):
        logger.info(f"Received voice response event: {data['type']} for message {data['id']}")
        
        if data['type'] == "chunk":
            # Handle speech chunk
            await state_machine.on_response_chunk(data['id'], data['text'])
        elif data['type'] == "completed":
            # Handle speech complete
            await state_machine.on_response_complete(data['id'], data['text'])
    voice_response_listener_task = asyncio.create_task(
        voice_response_subscriber.listen(onVoiceResponse)
    )

    # Handle transcription completed events from the broker
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

    state_machine.transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)
    state_machine.transcriber.add_event_listener("transcription_error", onTranscriptionError)

    # start session manager ------------------------------------------------------------
    await state_machine.start()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await voice_response_listener_task
    await input_listener_task
    await input_subsciber.close()
    await state_machine.close()
    await voice_command_publisher.close()

async def main_bak():
    print("Starting YOVA - Your Own Voice Assistant...")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    # Create state machine
    state_machine = StateMachine(
        logger,
        SpeechHandler(logger, api_key),
        RealtimeTranscriber(OpenAiTranscriptionProvider(api_key, logger), logger=logger)
    )

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

    # Create broker subscriber for input
    input_subsciber = Subscriber()
    await input_subsciber.connect()
    await input_subsciber.subscribe("input")

    # Handle input events from the broker
    async def onInput(topic, data):
        if data['active'] == True:
            await state_machine.on_input_activated()
        else:
            await state_machine.on_input_deactivated()
    
    # Handle voice response events from the broker
    async def onVoiceResponse(topic, data):
        logger.info(f"Received voice response event: {data['type']} for message {data['id']}")
        
        if data['type'] == "chunk":
            # Handle speech chunk
            await state_machine.on_response_chunk(data['id'], data['text'])
        elif data['type'] == "completed":
            # Handle speech complete
            await state_machine.on_response_complete(data['id'], data['text'])

    # Handle voice command detection events from the broker
    async def onVoiceCommandDetected(topic, data):
        logger.info(f"Received voice command detection event: {data['transcript']}")
        
        # Handle transcription completed logic
        await state_machine.transcriber.stop_audio_recording()
        print("PROMPT: ", data['transcript'])

    # Start listening for voice command events
    voice_command_listener_task = asyncio.create_task(
        voice_command_subscriber.listen(onVoiceCommandDetected)
    )
    
    # Start listening for voice response events
    voice_response_listener_task = asyncio.create_task(
        voice_response_subscriber.listen(onVoiceResponse)
    )

    # Start listening for input events
    input_listener_task = asyncio.create_task(
        input_subsciber.listen(onInput)
    )

    # Handle transcription completed events from the broker
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

    state_machine.transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)
    state_machine.transcriber.add_event_listener("transcription_error", onTranscriptionError)

    # start session manager ------------------------------------------------------------
    await state_machine.transcriber.start_realtime_transcription()
    await state_machine.speech_handler.start()
    await state_machine.transcriber.start_audio_recording()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await voice_command_listener_task
    await voice_response_listener_task
    await input_listener_task
    await voice_command_subscriber.close()
    await voice_response_subscriber.close()
    await voice_command_publisher.close()
    await input_subsciber.close()
    await state_machine.speech_handler.stop()
    await state_machine.transcriber.stop_realtime_transcription()


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
