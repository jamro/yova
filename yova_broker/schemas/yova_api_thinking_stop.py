"""
Schema for yova.api.thinking.stop event
"""

YOVA_API_THINKING_STOP = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the thinking operation"
        }
    },
    "required": ["id"],
    "additionalProperties": False
}
