"""
Broker monitoring functionality for YOVA Broker
"""

import asyncio
import logging
from typing import Optional
from .broker import YovaBroker
from .client import Subscriber


class BrokerMonitor:
    """Class for monitoring all events in YOVA Broker"""
    
    def __init__(self, broker: YovaBroker):
        """Initialize the broker monitor with a broker instance"""
        self.broker = broker
        self.logger = logging.getLogger(">>> EVENT")
        self.subscriber: Optional[Subscriber] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Configure logger specifically for this class
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logger for this class"""
        # Create a formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s %(message)s'
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
    
    async def message_handler(self, topic: str, data: any):
        """Handle incoming messages by logging them"""
        self.logger.info(f"[{topic}] -> {data}")
    
    async def start_monitoring(self):
        """Start monitoring all events from the broker"""
        if self.running:
            self.logger.warning("Monitoring is already running")
            return
        
        try:
            # Create subscriber and connect to broker
            self.subscriber = Subscriber()
            await self.subscriber.connect()
            
            # Subscribe to all topics (empty string for wildcard subscription)
            await self.subscriber.subscribe("")
            
            # Start listening for messages
            self.running = True
            self.monitoring_task = asyncio.create_task(
                self.subscriber.listen(self.message_handler)
            )
            
            self.logger.info("Broker monitoring started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop monitoring and cleanup resources"""
        if not self.running:
            return
        
        self.logger.info("Stopping broker monitoring...")
        self.running = False
        
        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close subscriber
        if self.subscriber:
            await self.subscriber.close()
            self.subscriber = None
        
        self.logger.info("Broker monitoring stopped")
    
    async def run_monitor(self):
        """Run the broker monitor (alias for start_monitoring)"""
        await self.start_monitoring()
        
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
            
