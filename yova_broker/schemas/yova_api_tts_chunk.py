"""
Schema for yova.api.tts.chunk event
"""

YOVA_API_TTS_CHUNK = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the TTS chunk"
        },
        "content": {
            "type": "string",
            "description": "Text content or base64-encoded audio data for speech conversion"
        },
        "priority_score": {
            "type": "number",
            "description": "Priority score for the chunk. When higher priority audio chunks are in playback queue, lower priority chunks are skipped."
        }
    },
    "required": ["id", "content"],
    "additionalProperties": False
}
