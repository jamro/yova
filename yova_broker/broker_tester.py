"""
Broker testing functionality for YOVA Broker
"""

import asyncio
import logging
from .broker import YovaBroker
from .client import Publisher, Subscriber


class BrokerTester:
    """Class for testing YOVA Broker functionality"""
    
    def __init__(self, broker: YovaBroker):
        """Initialize the broker tester with a broker instance"""
        self.broker = broker
        self.logger = logging.getLogger(__name__)
        
        # Configure logger specifically for this class
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logger for this class"""
        # Create a formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create a handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Set log level
        self.logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
    
    async def run_test(self):
        """Run the broker test sequence"""
        await asyncio.sleep(1)
        self.logger.info("Testing broker...")
        
        # Create subscriber and publisher clients
        subscriber = Subscriber()
        publisher = Publisher()
        
        try:
            # Subscribe to test event
            await subscriber.subscribe("broker_test")
            await asyncio.sleep(1) 
            
            received_messages = []
            async def message_handler(topic, data):
                received_messages.append((topic, data))
            
            # Start listening in background
            listen_task = asyncio.create_task(subscriber.listen(message_handler))
            
            # Wait a bit more for the listener to be fully ready
            await asyncio.sleep(1)
            
            # Publish test event
            test_message = {"message": "Hello from test_broker!", "timestamp": asyncio.get_event_loop().time()}
            await publisher.publish("broker_test", test_message)
            
            # Wait longer for message to be received
            await asyncio.sleep(1)
            
            # Check if message was received
            if len(received_messages) == 1 and received_messages[0][0] == "broker_test" and received_messages[0][1] == test_message:
                self.logger.info("✅ Test successful! Message was received by subscriber")
            else:
                self.logger.warning("⚠️ Test incomplete - no messages received")
                self.logger.warning("This could indicate:")
                self.logger.warning("  1. Subscription not properly established")
                self.logger.warning("  2. Message routing issue in broker")
                self.logger.warning("  3. Timing issue with ZeroMQ proxy")
                self.logger.warning("  4. Message format mismatch")
                
                # Try to debug the issue
                self.logger.info("🔍 Debugging info:")
                self.logger.info(f"  - Broker frontend port: {self.broker.frontend_port}")
                self.logger.info(f"  - Broker backend port: {self.broker.backend_port}")
                self.logger.info(f"  - Publisher URL: tcp://localhost:{self.broker.frontend_port}")
                self.logger.info(f"  - Subscriber URL: tcp://localhost:{self.broker.backend_port}")
                self.logger.info(f"  - Broker healthy: {self.broker.is_healthy()}")
            
            # Stop listening
            await subscriber.stop()
            await listen_task
            
        except Exception as e:
            self.logger.error(f"❌ Error during broker test: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            # Clean up clients
            await subscriber.close()
            await publisher.close()
            self.logger.info("🏁 Broker test completed")

