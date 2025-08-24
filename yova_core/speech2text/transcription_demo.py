from yova_shared import get_config, setup_logging, get_clean_logger
from yova_core.speech2text.realtime_api import RealtimeApi
import asyncio
from yova_core.speech2text.transcriber import Transcriber

async def main():
    api_key = get_config("open_ai.api_key")

    # Set up clean logging
    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    logger.info("TRANSCRIPTION DEMO")

    api = RealtimeApi(
        api_key, 
        logger,
        model="gpt-4o-transcribe",
        language="en",
        noise_reduction="near_field"
    )
    
    transcriber = Transcriber(logger, api, audio_logs_path=get_config("speech2text.audio_logs_path"))
    transcriber.prerecord_beep = "beep1.wav"
    await transcriber.initialize()

    await transcriber.start_listening()
    await asyncio.sleep(5)
    await transcriber.stop_listening()
    await transcriber.cleanup()
    




if __name__ == "__main__":
    asyncio.run(main())