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

## ZeroMQ Events

### `voice_command_detected`
- **Topic**: `voice_command_detected`
- **Data Structure**:
```json
{
  "id": "string",
  "transcript": "string",
  "timestamp": "float"
}
```
- **Description**: Published when a voice command is detected and transcribed
- **Use Case**: External systems can listen for voice commands to trigger actions, home automation, or logging
- **Example**: Smart home systems can subscribe to detect when users say "turn on the lights"

### `voice_response`
- **Topic**: `voice_response`
- **Data Structure**:
```json
{
  "type": "chunk|completed|processing_started|processing_completed",
  "id": "string",
  "content": "string",
  "timestamp": "float"
}
```
- **Description**: Published when voice response chunks are received or when a complete response is finished
- **Types**:
  - **`chunk`**: Individual text chunks as they arrive from the AI service. Instead of text you can send base64 encoded audio data (e.g. data:audio/wav;base64,UklGRiQA...)
  - **`completed`**: Final complete response when the AI has finished generating
  - **`processing_started`**: Published when the AI is processing the request. Text is empty.
  - **`processing_completed`**: Published when the AI has finished processing the request. content is empty.
- **Use Case**: External systems can monitor AI responses in real-time, implement streaming UI updates, or trigger actions based on response completion
- **Example**: Web interfaces can subscribe to show real-time typing indicators and update displays as responses stream in

### `broker_test`
- **Topic**: `broker_test`
- **Data Structure**:
```json
{
  "message": "Hello from test_broker!",
  "timestamp": "float"
}
```
- **Description**: Test event used to verify broker functionality
- **Use Case**: Testing and debugging the ZeroMQ broker during development

### `input`
- **Topic**: `input`
- **Data Structure**:
```json
{
  "active": "boolean",
  "timestamp": "float"
}
```
- **Description**: Published when the input status changes in the development tools UI
- **Data**:
  - **`active: true`**: Published when input is activated (status becomes active)
  - **`active: false`**: Published when input is deactivated (status becomes inactive)
  - **`timestamp`**: Unix timestamp when the input status changed
- **Use Case**: External systems can monitor input activation status to coordinate with voice processing, implement input state synchronization, or trigger actions based on input availability
- **Example**: Voice processing systems can subscribe to pause/resume audio recording based on input activation status

### `state`
- **Topic**: `state`
- **Data Structure**:
```json
{
  "previous_state": "string",
  "new_state": "string",
  "timestamp": "float"
}
```
- **Description**: Published when the voice assistant's internal state machine transitions between different states
- **States**:
  - **`idle`**: Default state when the system is waiting for input
  - **`listening`**: Active state when recording and transcribing audio input
  - **`speaking`**: Active state when generating and playing back AI responses
- **Data**:
  - **`previous_state`**: The state the system was in before the transition
  - **`new_state`**: The state the system transitioned to
  - **`timestamp`**: Unix timestamp when the state change occurred
- **Use Case**: External systems can monitor the voice assistant's operational state to coordinate activities, implement state-aware UI updates, or trigger actions based on state transitions
- **Example**: Dashboard applications can subscribe to show real-time status indicators, or home automation systems can adjust behavior based on whether the assistant is listening, speaking, or idle

### `audio`
- **Topic**: `audio`
- **Data Structure**:
```json
{
  "type": "playing|recording",
  "id": "string",
  "text": "string",
  "timestamp": "float"
}
```
- **Description**: Published when audio playback begins or recording starts for a specific message
- **Data**:
  - **`type`**: Either "playing" (audio playback started) or "recording" (audio recording started)
  - **`id`**: Unique identifier for the message
  - **`text`**: The text content - for "playing" events this contains the text being converted to speech, for "recording" events this field is empty since transcription hasn't occurred yet
  - **`timestamp`**: Unix timestamp when the audio event started
- **Use Case**: External systems can monitor when audio playback begins to coordinate with other audio sources, implement audio state synchronization, or trigger actions based on speech output. Recording events can be used to indicate when the system is actively listening.
- **Example**: Audio mixing systems can subscribe to pause other audio sources when the assistant starts speaking, or logging systems can track which messages are being played back. Recording events can trigger visual indicators or mute other audio inputs.
