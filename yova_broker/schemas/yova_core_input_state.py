"""
Schema for yova.core.input.state event
"""

YOVA_CORE_INPUT_STATE = {
    "type": "object",
    "properties": {
        "active": {
            "type": "boolean",
            "description": "Input activation status - true if active, false if inactive"
        }
    },
    "required": ["active"],
    "additionalProperties": False
}
