# TTS Chunk Event

## Topic
`yova.api.tts.chunk`

## Data Structure
```json
{
  "id": "string",
  "content": "string",
  "timestamp": "float"
}
```

## Description
Published by the API connector to convert backend API responses into speech output. This event handles text chunks for speech conversion.

## Purpose
Designed for streaming APIs to reduce latency. Yova aggregates chunks into sentences and processes them sentence-by-sentence.

## Pro Tips
- **Keep the first sentence short** for faster speech generation
- **Advanced usage**: You can send base64-encoded audio (e.g., `data:audio/wav;base64,UklGRiQA...`) instead of text - Yova will play the audio directly

## Use Case
Enables API connectors to stream AI responses from backend API as speech and provide real-time feedback.
