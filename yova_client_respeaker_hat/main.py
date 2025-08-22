import sys

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
 
import time
import signal
import asyncio
from queue import Queue, Empty
from yova_shared.broker import Publisher, Subscriber
from yova_shared import setup_logging, get_clean_logger
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

        await publisher.publish("input", {
            "active": is_active,
            "timestamp": asyncio.get_event_loop().time()
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
            await asyncio.sleep(0.01)
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

    async def on_state_changed(topic, data):
        if data['new_state'] == "listening":
            animator.play('listening', repetitions=0, brightness=0.5)
        elif data['new_state'] == "idle":
            animator.stop()
    state_subscriber = Subscriber()
    await state_subscriber.connect()
    await state_subscriber.subscribe("state")
    asyncio.create_task(state_subscriber.listen(on_state_changed))

    async def on_audio(topic, data):
        if data['type'] == "playing":
            animator.play('speaking', repetitions=0, brightness=0.1)

    audio_subsciber = Subscriber()
    await audio_subsciber.connect()
    await audio_subsciber.subscribe("audio")
    asyncio.create_task(audio_subsciber.listen(on_audio))

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
