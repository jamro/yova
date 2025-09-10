"""
Schema for yova.core.audio.play.start event
"""

YOVA_CORE_AUDIO_PLAY_START = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the audio playback session"
        },
        "text": {
            "type": "string",
            "description": "The text being converted to speech"
        }
    },
    "required": ["id", "text"],
    "additionalProperties": False
}
