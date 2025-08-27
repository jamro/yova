# Backend Integration Guide

This guide explains how to integrate your backend service with YOVA using different transport methods. The integration follows a simple pattern where your service subscribes to voice commands and publishes speech responses.

## Integration Pattern

The basic integration follows this flow:

1. **Subscribe** to `yova.api.asr.result` to receive voice command transcriptions
2. **Process** the voice command in your backend service
3. **Publish** `yova.api.tts.chunk` for each response chunk
4. **Publish** `yova.api.tts.complete` when the response is finished

## Event Flow

```mermaid
sequenceDiagram
    participant User
    participant YOVA Core
    participant API Connector
    participant Your Backend
    
    User->>YOVA Core: Push-to-talk + speak
    YOVA Core->>API Connector: yova.api.asr.result
    API Connector->>Your Backend: Process command
    Your Backend->>API Connector: Response
    API Connector->>YOVA Core: yova.api.tts.chunk
    API Connector->>YOVA Core: yova.api.tts.complete
    YOVA Core->>User: Play speech response
```

## Getting Started with Examples

For a hands-on approach to integration, see the [API Connector Example](api_connector_example.md) guide. This  tutorial walks you through building a working echo connector that demonstrates the complete integration pattern, from receiving voice commands to generating speech responses. The example includes step-by-step implementation, testing procedures, and troubleshooting tips to help you get started quickly.

## Related Documentation

- [Architecture Overview](architecture.md) - Learn about YOVA's system architecture and components
- [Events Reference](events.md) - Complete list of events and their payloads
- [API Connector Example](api_connector_example.md) - Step-by-step guide to building your own API connector

