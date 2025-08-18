"""
Client library for interacting with YOVA Broker
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class Publisher:
    """ZeroMQ publisher client for sending messages to the broker"""
    
    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        self.broker_url = broker_url
        self.context = zmq.asyncio.Context()
        self.socket = None
        
    async def connect(self):
        """Connect to the broker"""
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(self.broker_url)
        logger.info(f"Publisher connected to {self.broker_url}")
        
    async def publish(self, topic: str, message: Any):
        """Publish a message to a topic"""
        if not self.socket:
            await self.connect()
            
        # Format: topic + separator + message
        full_message = f"{topic} {json.dumps(message)}"
        await self.socket.send_string(full_message)
        logger.debug(f"Published to {topic}: {message}")
        
    async def close(self):
        """Close the publisher connection"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()


class Subscriber:
    """ZeroMQ subscriber client for receiving messages from the broker"""
    
    def __init__(self, broker_url: str = "tcp://localhost:5556"):
        self.broker_url = broker_url
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.running = False
        
    async def connect(self):
        """Connect to the broker"""
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.broker_url)
        logger.info(f"Subscriber connected to {self.broker_url}")
        
    async def subscribe(self, topic: str):
        """Subscribe to a topic"""
        if not self.socket:
            await self.connect()
            
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        logger.info(f"Subscribed to topic: {topic}")
        
    async def listen(self, callback: Callable[[str, Any], None]):
        """Listen for messages and call the callback function"""
        if not self.socket:
            await self.connect()
            
        self.running = True
        logger.info("Starting to listen for messages...")
        
        try:
            while self.running:
                try:
                    message = await self.socket.recv_string()
                    topic, data = message.split(' ', 1)
                    message_data = json.loads(data)
                    callback(topic, message_data)
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
