"""
Schema for yova.api.tts.complete event
"""

YOVA_API_TTS_COMPLETE = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the TTS completion"
        },
        "content": {
            "type": "string",
            "description": "Final content summary for the completed TTS operation"
        }
    },
    "required": ["id", "content"],
    "additionalProperties": False
}
