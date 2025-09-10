"""
Schema for yova.api.thinking.start event
"""

YOVA_API_THINKING_START = {
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
