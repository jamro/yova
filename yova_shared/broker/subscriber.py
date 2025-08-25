"""
Subscriber client for interacting with YOVA Broker
"""

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)

class Subscriber:
    """ZeroMQ subscriber client for receiving messages from the broker"""
    
    def __init__(self, broker_url: str = "tcp://localhost:5556"):
        self.broker_url = broker_url
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.running = False
        
    async def connect(self, max_retries: int = 3, retry_delay: float = 0.5):
        """Connect to the broker with retry mechanism"""
        if self.socket:
            return  # Already connected
            
        for attempt in range(max_retries):
            try:
                self.socket = self.context.socket(zmq.SUB)
                self.socket.connect(self.broker_url)
                
                # Wait a moment for connection to stabilize
                await asyncio.sleep(0.1)
                
                logger.info(f"Subscriber connected to {self.broker_url} (attempt {attempt + 1})")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    if self.socket:
                        self.socket.close()
                        self.socket = None
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts: {e}")
                    raise
        
    async def subscribe(self, topic: str):
        """Subscribe to a topic"""
        if not self.socket:
            await self.connect()
            
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        
        # Wait a moment for subscription to be processed
        await asyncio.sleep(0.1)
        
        logger.info(f"Subscribed to topic: {topic}")

    async def subscribe_all(self, topics: list[str]):
        """Subscribe to all topics"""
        if not self.socket:
            await self.connect()
            
        for topic in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)

        await asyncio.sleep(0.1)
        logger.info(f"Subscribed to topics: {topics}")
        
    async def listen(self, callback: Callable[[str, Any], Awaitable[None]]):
        """Listen for messages and call the callback function"""
        if not self.socket:
            await self.connect()
            
        self.running = True
        logger.info("Starting to listen for messages...")
        
        # Wait a moment for the listener to be fully ready
        await asyncio.sleep(0.2)

        async def safe_callback(cb, topic, data):
            try:
                await cb(topic, data)
            except Exception as e:
                logger.exception(f"Callback failed: {e}")
        
        try:
            while self.running:
                try:
                    message = await self.socket.recv_string()
                    topic, data = message.split(' ', 1)
                    message_data = json.loads(data)
                    asyncio.create_task(safe_callback(callback, topic, message_data))
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            logger.info("Listening cancelled")
        finally:
            self.running = False
            
    async def stop(self):
        """Stop listening for messages"""
        self.running = False
        
    async def close(self):
        """Close the subscriber connection"""
        await self.stop()
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
