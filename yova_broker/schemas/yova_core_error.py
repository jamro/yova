"""
Schema for yova.core.error event
"""

YOVA_CORE_ERROR = {
    "type": "object",
    "properties": {
        "error": {
            "type": "string",
            "minLength": 1,
            "description": "Error message describing what went wrong"
        },
        "details": {
            "type": "string",
            "description": "Additional error details for debugging"
        }
    },
    "required": ["error"],
    "additionalProperties": False
}
