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
- **Description**: Event triggered when Yova detects a voice command. The event is published after the user releases the push-to-talk button and the recorded audio has been transcribed. It contains the transcription text and is used by the API connector to forward the command to the backend API.
- **Use Case**: API connectors can listen for voice commands to forward them to backend services, trigger actions, or log user interactions


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
- **Description**: Published by the API connector to convert backend API responses into speech output
- **Types**:
  - **`chunk`**: Text chunk for speech conversion. Designed for streaming APIs to reduce latency. Yova aggregates chunks into sentences and processes them sentence-by-sentence. *Pro tip*: Keep the first sentence short for faster speech generation. *Advanced*: You can send base64-encoded audio (e.g., `data:audio/wav;base64,UklGRiQA...`) instead of text - Yova will play the audio directly.
  - **`completed`**: Signals that all response chunks have been sent and finalizes the speech conversion process
  - **`processing_started`/`processing_completed`**: Used to display "thinking" indicators (e.g., LED animations on respeaker HAT)
- **Use Case**: Enables API connectors to stream AI responses from backend API as speech and provide real-time feedback

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
- **Description**: Published when the voice assistant's internal state machine transitions between different operational states
- **States**:
  - **`idle`**: Default state when the system is waiting for input
  - **`listening`**: Active state when recording audio input
  - **`speaking`**: Active state when generating and playing back speech responses
- **Data**:
  - **`previous_state`**: The state the system was in before the transition
  - **`new_state`**: The state the system transitioned to
  - **`timestamp`**: Unix timestamp when the state change occurred
- **Use Case**: Used internally by Yova to track state transitions. Useful for user interfaces to represent current Yova operational status.

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
- **Description**: Published when recording of audio input or playing of audio output begins
- **Data**:
  - **`type`**: Either "playing" (audio playback started) or "recording" (audio recording started)
  - **`id`**: Unique identifier for the message
  - **`text`**: The text content - for "playing" events this contains the text being converted to speech, for "recording" events this field is empty since transcription hasn't occurred yet
  - **`timestamp`**: Unix timestamp when the audio event started
- **Use Case**: Used internally by Yova to track state transitions. Useful for user interfaces to represent current Yova operational status

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
