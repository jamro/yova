import asyncio
from yova_core.speech2text import Transcriber, RealtimeApi
from yova_shared import setup_logging, get_clean_logger, get_config
from yova_core.text2speech.speech_handler import SpeechHandler
from yova_shared.broker import Publisher, Subscriber  
from yova_core.state_machine import StateMachine
from yova_core.voice_id.voice_id_manager import VoiceIdManager
import numpy as np
import base64
from yova_core.speech2text.apm import YovaPipeline
from yova_core.speech2text.batch_api import BatchApi
from yova_core.cost_tracker import CostTracker

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

    # config cost tracker
    cost_tracker = CostTracker(logger)

    # Create state machine
    if get_config("speech2text.streaming"):
        logger.info("Using streaming transcription API")
        transcription_api = RealtimeApi(
            api_key, 
            logger,
            model=get_config("speech2text.model"),
            language=get_config("speech2text.language"),
            noise_reduction=get_config("speech2text.noise_reduction"),
            instructions=get_config("speech2text.instructions"),
            cost_tracker=cost_tracker
        )
    else:
        logger.info("Using batch transcription API")
        transcription_api = BatchApi(
            logger,
            api_key,
            model=get_config("speech2text.model"),
            prompt=get_config("speech2text.instructions"),
            cost_tracker=cost_tracker
        )

    state_machine = StateMachine(
        logger,
        SpeechHandler(logger, api_key, playback_config, cost_tracker),
        Transcriber(
            logger=logger,
            transcription_api=transcription_api,
            voice_id_manager=VoiceIdManager(
                logger,
                similarity_threshold=get_config("voice_id.threshold"),
            ) if get_config("voice_id.enabled") else None,
            preprocess_pipeline=YovaPipeline(
                logger, 
                high_pass_cutoff_freq=get_config("speech2text.preprocessing.high_pass_cutoff_freq") or None, 
                declicking=get_config("speech2text.preprocessing.declicking"), 
                noise_supresion_level=get_config("speech2text.preprocessing.noise_supresion_level") or None, 
                agc_enabled=get_config("speech2text.preprocessing.agc_enabled"), 
                vad_aggressiveness=get_config("speech2text.preprocessing.vad_aggressiveness") or None, 
                normalization_enabled=get_config("speech2text.preprocessing.normalization_enabled"), 
                normalization_target_rms_dbfs=get_config("speech2text.preprocessing.normalization_target_rms_dbfs"), 
                normalization_peak_limit_dbfs=get_config("speech2text.preprocessing.normalization_peak_limit_dbfs"), 
                edge_fade_enabled=get_config("speech2text.preprocessing.edge_fade_enabled")
            ),
            audio_logs_path=get_config("speech2text.audio_logs_path"),
            prerecord_beep=get_config("speech2text.prerecord_beep"),
            min_speech_length=get_config("speech2text.preprocessing.min_speech_length"),
            exit_on_error=True
        )
    )
    async def log_state_change(data):
        logger.info(f"State changed: {data['previous_state']} -> {data['new_state']}")
        await publisher.publish("core", "yova.core.state.change", {
            "previous_state": data['previous_state'],
            "new_state": data['new_state']
        })
    state_machine.add_event_listener("state_changed", log_state_change)

    # Create broker subscriber
    subscriber = Subscriber()
    await subscriber.connect()
    await subscriber.subscribe_all(["yova.api.tts.chunk", "yova.api.tts.complete", "yova.core.input.state"])
    
    async def on_message(topic, message):
        data = message['data']
        
        # yova.api.tts.chunk ================================================================
        if topic == "yova.api.tts.chunk":
            logger.info(f"Received voice response event: yova.api.tts.chunk for message {data['id']}")
            await state_machine.on_response_chunk(data['id'], data['content'])

        # yova.api.tts.complete ================================================================
        if topic == "yova.api.tts.complete":
            logger.info(f"Received voice response event: yova.api.tts.complete for message {data['id']}")
            await state_machine.on_response_complete(data['id'], data['content'])
        
        # input ========================================================================
        elif topic == "yova.core.input.state":
            if data['active'] == True:
                dt = asyncio.get_event_loop().time()*1000 - message['ts_ms']
                logger.info(f"Input activation event arrived after {dt} ms")
                await state_machine.on_input_activated()
            else:
                await state_machine.on_input_deactivated()

    listener_task = asyncio.create_task(subscriber.listen(on_message))

    # Handle transcription completed events from the broker
    async def on_transcription_completed(data):
        # Publish voice command detection event
        try:
            voice_id_payload = None
            if data['voice_id'] and get_config("voice_id.enabled"):
                embedding = data['voice_id']['embedding']
                emb32 = np.asarray(embedding, dtype=np.float32)
                embedding_payload = {
                    "embedding_base64": base64.b64encode(emb32.tobytes()).decode("ascii"),
                    "embedding_dtype": "float32",
                    "embedding_shape": list(emb32.shape)
                }

                voice_id_payload = {
                    "user_id": data['voice_id']['user_id'],
                    "similarity": data['voice_id']['similarity'],
                    "confidence_level": data['voice_id']['confidence_level'],
                    "embedding": embedding_payload if get_config("voice_id.include_embedding") else None
                }

            await publisher.publish("core", "yova.api.asr.result", {
                "id": str(data['id']),
                "transcript": data['transcript'],
                "voice_id": voice_id_payload
            })
        except Exception as e:
            logger.error(f"Failed to publish voice command detection event: {e}")

    async def on_playing_audio(data):
        await publisher.publish("core", "yova.core.audio.play.start", {
            "id": data["message_id"],
            "text": data["text"]
        })

    async def on_audio_recording_started(data):
        await publisher.publish("core", "yova.core.audio.record.start", {
            "id": data["id"]
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
