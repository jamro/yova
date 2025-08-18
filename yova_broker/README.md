# YOVA Broker

A ZeroMQ-based event hub for the YOVA system that provides reliable message routing between publishers and subscribers.

## Architecture

The broker uses ZeroMQ's XPUB/XSUB pattern:
- **Frontend (Port 5555)**: Accepts connections from publishers
- **Backend (Port 5556)**: Accepts connections from subscribers
- **Proxy**: Routes messages between frontend and backend

## Features

- Asynchronous message handling
- Topic-based message routing
- Simple publisher/subscriber client libraries
- Automatic reconnection handling
- JSON message serialization

## Usage

### Starting the Broker

```bash
# Start the broker service
poetry run yova-broker
```

### Using the Client Libraries

```python
from yova_broker.client import Publisher, Subscriber
import asyncio

# Publisher example
async def publish_messages():
    publisher = Publisher()
    await publisher.publish("user.voice", {"text": "Hello world"})
    await publisher.close()

# Subscriber example
async def listen_for_messages():
    subscriber = Subscriber()
    await subscriber.subscribe("user.voice")
    
    def handle_message(topic, message):
        print(f"Received: {message}")
    
    await subscriber.listen(handle_message)

# Run both
asyncio.run(asyncio.gather(
    publish_messages(),
    listen_for_messages()
))
```

### Running the Example

```bash
# Terminal 1: Start the broker
poetry run yova-broker

# Terminal 2: Run the example
poetry run python -m yova_broker.example
```

## Configuration

The broker can be configured with different ports:

```python
from yova_broker.broker import YovaBroker

broker = YovaBroker(
    frontend_port=5555,  # Publisher port
    backend_port=5556     # Subscriber port
)
```

## Integration with Supervisor

The broker is configured to run as a supervisor service alongside `yova_core`. Both services will start automatically and restart on failure.

## Dependencies

- `pyzmq`: ZeroMQ Python bindings
- `asyncio`: Asynchronous I/O support
