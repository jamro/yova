import asyncio
import os
from yova_core.speech2text import RealtimeTranscriber
from yova_core.speech2text.openai_transcription_provider import OpenAiTranscriptionProvider
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
    audio_publisher = Publisher()
    await audio_publisher.connect()

    # Create broker publisher for state events
    state_publisher = Publisher()
    await state_publisher.connect()

    # Create state machine
    transcription_provider = OpenAiTranscriptionProvider(api_key, logger,
        model=get_config("speech2text.model"),
        language=get_config("speech2text.language"),
        noise_reduction=get_config("speech2text.noise_reduction"),
        min_speech_length=get_config("speech2text.min_speech_length"),
        silence_amplitude_threshold=get_config("speech2text.silence_amplitude_threshold"),
        audio_buffer_age=get_config("speech2text.audio_buffer_age")
    )
    state_machine = StateMachine(
        logger,
        SpeechHandler(logger, api_key, playback_config),
        RealtimeTranscriber(
            transcription_provider, 
            logger=logger,
            audio_logs_path=get_config("speech2text.audio_logs_path"),
            prerecord_beep=get_config("speech2text.prerecord_beep"),
        )
    )
    async def log_state_change(data):
        logger.info(f"State changed: {data['previous_state']} -> {data['new_state']}")
        await state_publisher.publish("state", {
            "previous_state": data['previous_state'],
            "new_state": data['new_state'],
            "timestamp": asyncio.get_event_loop().time()
        })
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
                "id": str(data['id']),
                "transcript": data['transcript'],
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Failed to publish voice command detection event: {e}")

    async def onTranscriptionError(data):
        logger.error(f"Transcription error: {data['error']}")

    async def onPlayingAudio(data):
        await audio_publisher.publish("audio", {
            "type": "playing",
            "id": data["message_id"],
            "text": data["text"],
            "timestamp": asyncio.get_event_loop().time()
        })

    async def onAudioRecordingStarted(data):
        await audio_publisher.publish("audio", {
            "type": "recording",
            "id": data["id"],
            "text": "",
            "timestamp": asyncio.get_event_loop().time()
        })

    state_machine.transcriber.add_event_listener("transcription_completed", onTranscriptionCompleted)
    state_machine.transcriber.add_event_listener("transcription_error", onTranscriptionError)
    state_machine.speech_handler.add_event_listener("playing_audio", onPlayingAudio)
    state_machine.transcriber.add_event_listener("audio_recording_started", onAudioRecordingStarted)
    
    # start session manager ------------------------------------------------------------
    await state_machine.start()
    await asyncio.get_event_loop().run_in_executor(None, input)

    # stop session manager ------------------------------------------------------------
    await voice_response_listener_task
    await input_listener_task
    await input_subsciber.close()
    await state_machine.close()
    await voice_command_publisher.close()

def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
