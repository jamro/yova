import asyncio
from yova_core.speech2text import Transcriber, RealtimeApi
from yova_shared import setup_logging, get_clean_logger, get_config
from yova_core.text2speech.speech_handler import SpeechHandler
from yova_shared.broker import Publisher, Subscriber  
from yova_core.state_machine import StateMachine

async def main():
    print("Starting YOVA - Your Own Voice Assistant...")

    api_key = get_config("open_ai.api_key")

    if not api_key or len(api_key) < 20:
        raise ValueError("open_ai.api_key is not set")
    
    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    # Define playback configuration
    playback_config = {
        "model": get_config("text2speech.model"),
        "voice": get_config("text2speech.voice"),
        "speed": get_config("text2speech.speed"),
        "instructions": get_config("text2speech.instructions")
    }

    # Create broker publisher for audio events
    publisher = Publisher()
    await publisher.connect()

    # Create state machine
    state_machine = StateMachine(
        logger,
        SpeechHandler(logger, api_key, playback_config),
        Transcriber(
            logger=logger,
            realtime_api=RealtimeApi(
                api_key, 
                logger,
                model=get_config("speech2text.model"),
                language=get_config("speech2text.language"),
                noise_reduction=get_config("speech2text.noise_reduction"),
            ),
            audio_logs_path=get_config("speech2text.audio_logs_path"),
            prerecord_beep=get_config("speech2text.prerecord_beep"),
            min_speech_length=get_config("speech2text.min_speech_length"),
            silence_amplitude_threshold=get_config("speech2text.silence_amplitude_threshold"),
        )
    )
    async def log_state_change(data):
        logger.info(f"State changed: {data['previous_state']} -> {data['new_state']}")
        await publisher.publish("state", {
            "previous_state": data['previous_state'],
            "new_state": data['new_state'],
            "timestamp": asyncio.get_event_loop().time()
        })
    state_machine.add_event_listener("state_changed", log_state_change)

    # Create broker subscriber
    subscriber = Subscriber()
    await subscriber.connect()
    await subscriber.subscribe_all(["voice_response", "input"])
    
    async def on_message(topic, data):
        
        # voice command ================================================================
        if topic == "voice_response":
            logger.info(f"Received voice response event: {data['type']} for message {data['id']}")
            
            if data['type'] == "chunk":
                # Handle speech chunk
                await state_machine.on_response_chunk(data['id'], data['text'])
            elif data['type'] == "completed":
                # Handle speech complete
                await state_machine.on_response_complete(data['id'], data['text'])
        
        # input ========================================================================
        elif topic == "input":
            if data['active'] == True:
                dt = asyncio.get_event_loop().time() - data['timestamp']
                logger.info(f"Input activation event arrived after {dt} seconds")
                await state_machine.on_input_activated()
            else:
                await state_machine.on_input_deactivated()

    listener_task = asyncio.create_task(subscriber.listen(on_message))

    # Handle transcription completed events from the broker
    async def on_transcription_completed(data):
        # Publish voice command detection event
        try:
            await publisher.publish("voice_command_detected", {
                "id": str(data['id']),
                "transcript": data['transcript'],
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Failed to publish voice command detection event: {e}")

    async def on_playing_audio(data):
        await publisher.publish("audio", {
            "type": "playing",
            "id": data["message_id"],
            "text": data["text"],
            "timestamp": asyncio.get_event_loop().time()
        })

    async def on_audio_recording_started(data):
        await publisher.publish("audio", {
            "type": "recording",
            "id": data["id"],
            "text": "",
            "timestamp": asyncio.get_event_loop().time()
        })

    state_machine.transcriber.add_event_listener("transcription_completed", on_transcription_completed)
    state_machine.speech_handler.add_event_listener("playing_audio", on_playing_audio)
    state_machine.transcriber.add_event_listener("audio_recording_started", on_audio_recording_started)
    
    # start session manager ------------------------------------------------------------
    await state_machine.start()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await listener_task
    await subscriber.close()
    await state_machine.close()
    await publisher.close()

def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())

if __name__ == "__main__":
    run()
