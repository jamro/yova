"""
Schema for yova.core.state.change event
"""

YOVA_CORE_STATE_CHANGE = {
    "type": "object",
    "properties": {
        "previous_state": {
            "type": "string",
            "enum": ["idle", "listening", "speaking"],
            "description": "The previous state of the voice assistant"
        },
        "new_state": {
            "type": "string",
            "enum": ["idle", "listening", "speaking"],
            "description": "The new state of the voice assistant"
        }
    },
    "required": ["previous_state", "new_state"],
    "additionalProperties": False
}
