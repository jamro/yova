"""
Schema for yova.core.audio.record.start event
"""

YOVA_CORE_AUDIO_RECORD_START = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the audio recording session"
        }
    },
    "required": ["id"],
    "additionalProperties": False
}
