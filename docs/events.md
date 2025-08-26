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

## Event Categories

### 1. Voice Recognition Events

#### `yova.api.asr.result`
**When**: Triggered when YOVA detects and transcribes a voice command
**Publisher**: Core speech recognition system
**Subscribers**: API connectors, external systems

**Data Structure**:
```json
{
  "id": "string",
  "transcript": "string",
  "timestamp": "float"
}
```

**Description**: Published after the user releases the push-to-talk button and the recorded audio has been transcribed. Contains the transcription text that can be forwarded to backend APIs.

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
  "id": "string",
  "content": "string",
  "timestamp": "float"
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
  "id": "string",
  "content": "string",
  "timestamp": "float"
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
  "id": "string",
  "timestamp": "float"
}
```

**Description**: Triggers "thinking" indicators, such as UI spinners or LED animations, to show the system is processing a request. Event is optional, and can be omitted.

#### `yova.api.thinking.stop`
**When**: Backend API processing completes
**Publisher**: API connector
**Subscribers**: UI systems, LED controllers

```json
{
  "id": "string",
  "timestamp": "float"
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
  "previous_state": "string",
  "new_state": "string",
  "timestamp": "float"
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
  "id": "string",
  "text": "",
  "timestamp": "float"
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
  "id": "string",
  "text": "string",
  "timestamp": "float"
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
  "active": "boolean",
  "timestamp": "float"
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
  "message": "Hello from test_broker!",
  "timestamp": "float"
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
- **Use event IDs**: When available, use event IDs to correlate related events across your system
