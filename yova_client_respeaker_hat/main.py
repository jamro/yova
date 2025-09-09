import sys
import os

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO module not found.")
    print("This application requires Raspberry Pi GPIO access.")
    print("Please ensure you're running on a Raspberry Pi with RPi.GPIO installed.")
    print("Install with: pip install RPi.GPIO")
    sys.exit(1)

try:
    import spidev
except ImportError:
    print("Error: spidev module not found.")
    print("This application requires spidev access.")
    print("Please ensure you're running on a Raspberry Pi with spidev installed.")
    print("Install with: pip install spidev")
    sys.exit(1)
 
import asyncio
from queue import Queue, Empty
from yova_shared.broker import Publisher, Subscriber
from yova_shared import setup_logging, get_clean_logger, play_audio
from yova_client_respeaker_hat.anim import Animator

BUTTON_PIN = 17

animator = Animator()

# Global queue for button events
button_events = Queue()

def setup_gpio():
    """Setup GPIO configuration for button monitoring."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, callback=button_callback, bouncetime=50)

async def notify_input_state(is_active, logger):
    publisher = Publisher()
    try:
        await publisher.connect()

        await publisher.publish("client_respeaker_hat", "yova.core.input.state", {
            "active": is_active
        })
            
    except Exception as e:
        logger.error(f"Failed to publish to broker: {e}")
    finally:
        await publisher.close()

def button_callback(channel):
    """Callback function called when button state changes."""
    button_state = GPIO.input(BUTTON_PIN)
    button_events.put(button_state == GPIO.LOW)

async def process_button_events(logger):
    """Process button events from the queue."""
    while True:
        try:
            # Wait for button events with a timeout
            is_active = button_events.get(timeout=0.1)
            logger.info(f"Button {'PRESSED' if is_active else 'RELEASED'}")
            await notify_input_state(is_active, logger)
        except Empty:
            # No events, yield control to event loop
            await asyncio.sleep(0.02)
            continue
        except Exception as e:
            logger.error(f"Error processing button event: {e}")

def cleanup_gpio():
    """Clean up GPIO configuration."""
    try:
        # Remove event detection before cleanup
        GPIO.remove_event_detect(BUTTON_PIN)
        GPIO.cleanup()
        print("\nGPIO cleanup completed.")
    except Exception as e:
        print(f"\nError during GPIO cleanup: {e}")
    finally:
        print("Exiting...")

async def main_async():
    """Main async function to monitor button presses."""

    animator.play('welcome', repetitions=1, brightness=0.05)

    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    subscriber = Subscriber()
    await subscriber.connect()
    await subscriber.subscribe_all([
        "yova.core.state.change", 
        "yova.core.audio.play.start", 
        "yova.core.audio.record.start", 
        "yova.api.thinking.start",
        "yova.api.thinking.stop",
        "yova.core.error",
        "yova.api.error"
    ])

    async def on_message(topic, message):
        data = message['data']
        
        # yova.core.audio.play.start ========================================================================
        if topic == "yova.core.audio.play.start":
            logger.info("Playing speaking animation")
            animator.play('speaking', repetitions=0, brightness=0.1)
        
        # yova.core.audio.record.start ========================================================================
        if topic == "yova.core.audio.record.start":
            logger.info("Playing listening animation")
            animator.play('listening', repetitions=0, brightness=0.5)

        # yova.core.state.change ========================================================================
        if topic == "yova.core.state.change":
            if data['new_state'] == "idle":
                logger.info("Stopping animation")
                animator.stop()

        # yova.api.thinking.start ========================================================================
        if topic == "yova.api.thinking.start":
            logger.info("Playing thinking animation")
            animator.play('thinking', repetitions=0, brightness=0.1)

        # yova.api.thinking.stop ========================================================================
        if topic == "yova.api.thinking.stop":
            if animator.get_current_animation_id() == "thinking":
                logger.info("Stopping thinking animation")
                animator.stop()
  
        # yova.*.error ========================================================================
        if topic == "yova.core.error" or topic == "yova.api.error":
            logger.info("Playing error animation")
            animator.play('error', repetitions=2, brightness=0.5)

            error_file_path = os.path.join(os.path.dirname(__file__), "..", "yova_shared", "assets", "error.wav")
            
            # Play error sound
            try:
                logger.info("Playing error sound")
                await play_audio(error_file_path, volume_gain=-10)  # Reduce volume by 10dB
            except Exception as e:
                logger.error(f"Failed to play error sound: {e}")
            
    
    # start subscriber
    asyncio.create_task(subscriber.listen(on_message))

    logger.info("Starting GPIO Button Monitor...")
    logger.info(f"Monitoring GPIO{BUTTON_PIN} for button presses")

    try:
        setup_gpio()
        
        # Start processing button events concurrently with subscriber
        button_task = asyncio.create_task(process_button_events(logger))
        
        # Wait for both tasks to complete (or until interrupted)
        await asyncio.gather(button_task, return_exceptions=True)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        cleanup_gpio()

def run():
    """Main function to run the async event loop."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    run()
