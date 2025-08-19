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

### 1. Voice Command Events

#### `voice_command_detected`
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

#### `broker_test`
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
