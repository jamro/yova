"""
Broker validator functionality for YOVA Broker
"""

import asyncio
import logging
from typing import Optional
import jsonschema
from jsonschema import ValidationError
from yova_broker.broker import YovaBroker
from yova_shared.broker import Subscriber
from yova_shared import get_clean_logger
from yova_broker.schemas import ENVELOPE_SCHEMA, ALL_EVENTS

class BrokerValidator:
    """Class for validating all events in YOVA Broker"""
    
    def __init__(self, broker: YovaBroker):
        """Initialize the broker validator with a broker instance"""
        self.broker = broker
        self.logger = logging.getLogger('broker_validator')
        self.subscriber: Optional[Subscriber] = None
        self.validation_task: Optional[asyncio.Task] = None
        self.running = False
    
    
    async def message_handler(self, topic: str, message: any):
        """Handle incoming messages by validating them with JSON schema"""
        try:
            # Validate the message envelope
            jsonschema.validate(instance=message, schema=ENVELOPE_SCHEMA)

            event = message['event']
            event_schema_id = event.replace(".", "_").upper()
            if event_schema_id not in ALL_EVENTS:
                self.logger.warning(f"Event '{event}' not supported")
                return
            event_schema = ALL_EVENTS[event_schema_id]
            jsonschema.validate(instance=message['data'], schema=event_schema)
            
        except ValidationError as e:
            # Extract more detailed error information
            error_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            actual_value = e.instance if e.absolute_path else "N/A"
            
            self.logger.warning(f"Message validation failed for topic '{topic}':")
            self.logger.warning(f"  Error at path '{error_path}': {e.message}")
            self.logger.warning(f"  Expected: {e.schema.get('const', 'N/A') if 'const' in e.schema else 'N/A'}")
            self.logger.warning(f"  Actual value: {actual_value}")
            self.logger.warning(f"  Invalid message: {message}")
        except Exception as e:
            self.logger.error(f"Unexpected error during message validation for topic '{topic}': {e}")
            self.logger.error(f"Message that caused error: {message}")
    
    async def start_validation(self):
        """Start validation all events from the broker"""
        if self.running:
            self.logger.warning("Validation is already running")
            return
        
        try:
            # Create subscriber and connect to broker
            self.subscriber = Subscriber()
            await self.subscriber.connect()
            
            # Subscribe to all topics (empty string for wildcard subscription)
            await self.subscriber.subscribe("")
            
            # Start listening for messages
            self.running = True
            self.validation_task = asyncio.create_task(
                self.subscriber.listen(self.message_handler)
            )
            
            self.logger.info("Broker validator started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start validation: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop validation and cleanup resources"""
        if not self.running:
            return
        
        self.logger.info("Stopping broker validator...")
        self.running = False
        
        # Cancel validation task
        if self.validation_task and not self.validation_task.done():
            self.validation_task.cancel()
            try:
                await self.validation_task
            except asyncio.CancelledError:
                pass
        
        # Close subscriber
        if self.subscriber:
            await self.subscriber.close()
            self.subscriber = None
        
        self.logger.info("Broker validator stopped")
    
    async def run_validator(self):
        """Run the broker validator (alias for start_validation)"""
        await self.start_validation()
        
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_validation()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
            
