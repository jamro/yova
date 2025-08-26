"""
Publisher client for interacting with YOVA Broker
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)

class Publisher:
    """ZeroMQ publisher client for sending messages to the broker"""
    
    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        self.broker_url = broker_url
        self.context = zmq.asyncio.Context()
        self.socket = None
        
    async def connect(self, max_retries: int = 3, retry_delay: float = 0.5):
        """Connect to the broker with retry mechanism"""
        if self.socket:
            return  # Already connected
            
        for attempt in range(max_retries):
            try:
                self.socket = self.context.socket(zmq.PUB)
                self.socket.connect(self.broker_url)
                
                # Wait a moment for connection to stabilize
                await asyncio.sleep(0.1)
                
                logger.info(f"Publisher connected to {self.broker_url} (attempt {attempt + 1})")
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
        
    async def publish(self, source: str, topic: str, message: Any):
        """Publish a message to a topic"""
        if not self.socket:
            await self.connect()
            
        # Format: topic + separator + message

        message_json = {
            "v": 1,
            "event": topic,
            "msg_id": f"uuid-{uuid.uuid4()}",
            "source": source,
            "ts_ms": int(time.time() * 1000),
            "data": message
        }

        full_message = f"{topic} {json.dumps(message_json)}"
        await self.socket.send_string(full_message)
        logger.debug(f"Published to {topic}: {message}")
        
    async def close(self):
        """Close the publisher connection"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
