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
  "transcript": "string",
  "timestamp": "float",
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
  "type": "chunk|completed",
  "id": "string",
  "text": "string",
  "timestamp": "float"
}
```
- **Description**: Published when voice response chunks are received or when a complete response is finished
- **Types**:
  - **`chunk`**: Individual text chunks as they arrive from the AI service
  - **`completed`**: Final complete response when the AI has finished generating
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
  "active": "boolean"
}
```
- **Description**: Published when the input status changes in the development tools UI
- **Data**:
  - **`active: true`**: Published when input is activated (status becomes active)
  - **`active: false`**: Published when input is deactivated (status becomes inactive)
- **Use Case**: External systems can monitor input activation status to coordinate with voice processing, implement input state synchronization, or trigger actions based on input availability
- **Example**: Voice processing systems can subscribe to pause/resume audio recording based on input activation status
