"""
Schema for yova.api.usage.occur event
"""

YOVA_API_USAGE_OCCUR = {
    "type": "object",
    "properties": {
        "cost": {
            "type": "number",
            "minimum": 0,
            "description": "The cost of the operation in USD"
        },
        "extra_data": {
            "type": "object",
            "description": "Optional data about the operation to be stored in the usage log"
        }
    },
    "required": ["cost"],
    "additionalProperties": False
}
