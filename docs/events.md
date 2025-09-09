# YOVA ZeroMQ Events Documentation

This document describes all ZeroMQ events in the YOVA (Your Own Voice Assistant) system for inter-process communication.

## Overview

YOVA uses ZeroMQ as a message broker for distributed event communication between different processes and external systems. The broker enables loose coupling between components and allows external systems to subscribe to voice assistant events.

## ZeroMQ Broker Architecture

The YOVA broker uses ZeroMQ's XPUB/XSUB pattern:
- **Frontend Port (5555)**: Publishers connect here to send messages
- **Backend Port (5556)**: Subscribers connect here to receive messages
- **Message Format**: `topic json_data` where topic is a string and data is JSON-serialized
- **Protocol**: TCP-based communication for reliable message delivery

## Event Envelope Structure

All YOVA events follow a standardized envelope format that provides metadata and context for each message:

```json
{
  "v": 1,
  "event": "yova.asr.result",        // also equals topic path
  "msg_id": "uuid-...",              // unique per message
  "source": "asr",                   // module name
  "ts_ms": 1756115770123,            // Unix ms
  "data": { /* event-specific fields */ }
}
```

**Envelope Fields**:
- **`v`**: Version number for the envelope format (currently 1)
- **`event`**: The event topic/path that matches the ZeroMQ topic
- **`msg_id`**: Unique identifier for each message (UUID format)
- **`source`**: Name of the module that published the event
- **`ts_ms`**: Unix timestamp in milliseconds when the event was created
- **`data`**: Event-specific payload containing the actual event data

**Note**: The `event` field in the envelope always matches the ZeroMQ topic path, making it easy to correlate messages with their topics.

## Event Categories

### Complete Event List

- `yova.api.asr.result` - Voice command transcription result
- `yova.api.tts.chunk` - Text chunk ready for speech conversion
- `yova.api.tts.complete` - All response chunks sent
- `yova.api.thinking.start` - Backend API processing begins
- `yova.api.thinking.stop` - Backend API processing completes
- `yova.core.state.change` - State machine transitions (idle/listening/speaking)
- `yova.core.audio.record.start` - Audio recording begins
- `yova.core.audio.play.start` - Audio playback begins
- `yova.core.input.state` - Input activation status changes
- `yova.core.health.ping` - Test event for broker verification

---

### 1. Voice Recognition Events

#### `yova.api.asr.result`
**When**: Triggered when YOVA detects and transcribes a voice command
**Publisher**: Core speech recognition system
**Subscribers**: API connectors, external systems

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.api.asr.result",
  "msg_id": "uuid-1234-5678-9abc-def0",
  "source": "asr",
  "ts_ms": 1756115770123,
  "data": {
    "id": "string",
    "transcript": "string",
    "voice_id": {
      "user_id": "string",
      "similarity": "number",
      "confidence_level": "string",
      "embedding": {
        "embedding_base64": "string",
        "embedding_dtype": "string",
        "embedding_shape": ["number", "number", "number"]
      }
    }
  }
}
```

**Description**: Published after the user releases the push-to-talk button and the recorded audio has been transcribed. Contains the transcription text that can be forwarded to backend APIs.

If voice ID is enabled (see [config.md](config.md)), the `voice_id` field will be included in the payload:
- `user_id`: The ID of the identified user, or `null` if no user was identified
- `similarity`: The similarity score between the recorded audio and the user's voice (0.0 to 1.0)
- `confidence_level`: The confidence level of the identified user ("high", "medium", "low")
- `embedding`: if `include_embedding` is enabled in the config (see [config.md](config.md)), the embedding of the recorded audio will be included in the payload. This is a large payload, so it is not included by default.

More details in [Voice ID documentation](voice_id.md).

**Use Cases**:
- API connectors can listen for voice commands to forward to backend services
- Trigger actions based on voice input
- Log user interactions for analytics

---

### 2. Speech Output Events

#### `yova.api.tts.chunk`
**When**: Text chunk is ready for speech conversion
**Publisher**: API connector
**Subscribers**: Core text-to-speech system

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.api.tts.chunk",
  "msg_id": "uuid-1234-5678-9abc-def1",
  "source": "api_connector",
  "ts_ms": 1756115770124,
  "data": {
    "id": "string",
    "content": "string"
  }
}
```

**Description**: Designed for streaming APIs to reduce latency. YOVA aggregates chunks into sentences and processes them sentence-by-sentence.

**Pro Tips**:
- Keep the first sentence short for faster speech generation
- You can send base64-encoded audio (e.g., `data:audio/wav;base64,UklGRiQA...`) instead of text - YOVA will play the audio directly

#### `yova.api.tts.complete`
**When**: All response chunks have been sent
**Publisher**: API connector
**Subscribers**: Core text-to-speech system

```json
{
  "v": 1,
  "event": "yova.api.tts.complete",
  "msg_id": "uuid-1234-5678-9abc-def2",
  "source": "api_connector",
  "ts_ms": 1756115770125,
  "data": {
    "id": "string",
    "content": "string"
  }
}
```

**Description**: Signals that all response chunks have been sent and finalizes the speech conversion process.

---

### 3. Processing Status Events

#### `yova.api.thinking.start`
**When**: Backend API processing begins
**Publisher**: API connector
**Subscribers**: UI systems, LED controllers

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.api.thinking.start",
  "msg_id": "uuid-1234-5678-9abc-def3",
  "source": "api_connector",
  "ts_ms": 1756115770126,
  "data": {
    "id": "string"
  }
}
```

**Description**: Triggers "thinking" indicators, such as UI spinners or LED animations, to show the system is processing a request. Event is optional, and can be omitted.

#### `yova.api.thinking.stop`
**When**: Backend API processing completes
**Publisher**: API connector
**Subscribers**: UI systems, LED controllers

```json
{
  "v": 1,
  "event": "yova.api.thinking.stop",
  "msg_id": "uuid-1234-5678-9abc-def4",
  "source": "api_connector",
  "ts_ms": 1756115770127,
  "data": {
    "id": "string"
  }
}
```

**Description**: Signals that processing has finished and thinking indicators should stop. Event is optional, and can be omitted.

---

### 4. Core System State Events

#### `yova.core.state.change`
**When**: Voice assistant's internal state machine transitions
**Publisher**: Core state machine
**Subscribers**: UI systems, monitoring tools

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.core.state.change",
  "msg_id": "uuid-1234-5678-9abc-def5",
  "source": "core",
  "ts_ms": 1756115770128,
  "data": {
    "previous_state": "string",
    "new_state": "string"
  }
}
```

**Available States**:
- **`idle`**: Default state when the system is waiting for input
- **`listening`**: Active state when recording audio input
- **`speaking`**: Active state when generating and playing back speech responses

**Use Cases**:
- Track state transitions for debugging
- Update user interfaces to show current operational status
- Coordinate actions based on system state

---

### 5. Audio Activity Events

#### `yova.core.audio.record.start`
**When**: Audio recording begins
**Publisher**: Core audio system
**Subscribers**: UI systems, monitoring tools

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.core.audio.record.start",
  "msg_id": "uuid-1234-5678-9abc-def6",
  "source": "core",
  "ts_ms": 1756115770129,
  "data": {
    "id": "string"
  }
}
```

**Description**: Published when recording of audio input begins. The `text` field is empty since transcription hasn't occurred yet.

#### `yova.core.audio.play.start`
**When**: Audio playback begins
**Publisher**: Core audio system
**Subscribers**: UI systems, monitoring tools

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.core.audio.play.start",
  "msg_id": "uuid-1234-5678-9abc-def7",
  "source": "core",
  "ts_ms": 1756115770130,
  "data": {
    "id": "string",
    "text": "string"
  }
}
```

**Description**: Published when playing of audio output begins. The `text` field contains the text being converted to speech.

---

### 6. Input Status Events

#### `yova.core.input.state`
**When**: Input activation status changes
**Publisher**: Development tools UI
**Subscribers**: External systems, monitoring tools

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.core.input.state",
  "msg_id": "uuid-1234-5678-9abc-def8",
  "source": "dev_tools",
  "ts_ms": 1756115770131,
  "data": {
    "active": "boolean"
  }
}
```

**Description**: Published when the input status changes in the development tools UI.

**Data Values**:
- **`active: true`**: Input is activated (status becomes active)
- **`active: false`**: Input is deactivated (status becomes inactive)

**Use Cases**:
- Monitor input activation status to coordinate with voice processing
- Implement input state synchronization across systems
- Trigger actions based on input availability
- Pause/resume audio recording based on input activation status

---

### 7. System Health Events

#### `yova.core.health.ping`
**When**: Test event for broker verification
**Publisher**: Test systems
**Subscribers**: Monitoring tools

**Data Structure**:
```json
{
  "v": 1,
  "event": "yova.core.health.ping",
  "msg_id": "uuid-1234-5678-9abc-def9",
  "source": "test_system",
  "ts_ms": 1756115770132,
  "data": {
    "message": "Hello from test_broker!"
  }
}
```

**Description**: Test event used to verify broker functionality during development and testing.

**Use Cases**:
- Testing and debugging the ZeroMQ broker

## Best Practices

- **Subscribe to relevant events**: Only subscribe to events your system needs to avoid unnecessary processing
- **Handle event ordering**: Events may arrive out of order; use timestamps for sequencing when needed
- **Implement error handling**: Always handle cases where events might be malformed or missing
- **Monitor event frequency**: High-frequency events (like audio chunks) should be processed efficiently as they can block the main thread
- **Use event IDs**: Use the `msg_id` field from the envelope to correlate related events across your system
- **Validate envelope structure**: Always check the envelope fields (`v`, `event`, `source`, `ts_ms`) for proper message validation
- **Handle envelope versioning**: Check the `v` field to ensure compatibility with your event processing logic
