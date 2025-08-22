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
from yova_shared.broker.publisher import Publisher
from yova_shared import setup_logging, get_clean_logger

BUTTON_PIN = 17

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
            # No events, continue
            continue
        except Exception as e:
            logger.error(f"Error processing button event: {e}")

def cleanup_gpio():
    """Clean up GPIO configuration."""
    GPIO.cleanup()
    print("\nGPIO cleanup completed. Exiting...")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\nReceived interrupt signal. Cleaning up...")
    cleanup_gpio()
    sys.exit(0)

async def main_async():
    """Main async function to monitor button presses."""

    root_logger = setup_logging(level="INFO")
    logger = get_clean_logger("main", root_logger)

    logger.info("Starting GPIO Button Monitor...")
    logger.info(f"Monitoring GPIO{BUTTON_PIN} for button presses")
    
    try:
        setup_gpio()
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start processing button events
        await process_button_events(logger)
            
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
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    run()
