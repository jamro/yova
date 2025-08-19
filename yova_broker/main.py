"""
Main entry point for YOVA Broker service
"""

import asyncio
import logging
import signal
import sys
from yova_broker.broker import YovaBroker
from yova_broker.broker_tester import BrokerTester
from yova_broker.broker_monitor import BrokerMonitor


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


async def main():
    """Async main function for the YOVA Broker service"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    broker = YovaBroker()
    
    try:
        # Start the broker (this now returns immediately)
        await broker.start()
        
        # Run broker proxy and broker tester concurrently
        await asyncio.gather(
            broker.wait_for_proxy(),
            BrokerMonitor(broker).run_monitor(),
            BrokerTester(broker).run_test()
        )
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        logging.error(f"Broker error: {e}")
        
        # Check if it's a port binding error
        if "Address already in use" in str(e):
            logging.error("\n" + "="*60)
            logging.error("PORT BINDING ERROR DETECTED")
            logging.error("="*60)
            
            # Check both ports
            for port in [broker.frontend_port, broker.backend_port]:
                logging.error(f"\nInstructions for port {port}:")
                logging.error(broker.get_port_check_instructions(port))
            
            logging.error("\n" + "="*60)
            logging.error("SOLUTIONS:")
            logging.error("1. Stop the process using the busy port(s)")
            logging.error("2. Use different ports by modifying the YovaBroker constructor")
            logging.error("3. Wait for the port to become available")
            logging.error("="*60)
        
        sys.exit(1)
    finally:
        logging.info("Shutting down broker...")
        try:
            await broker.stop()
            logging.info("Broker shutdown completed")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
            sys.exit(1)


def run():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
