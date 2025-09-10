"""
Schema for yova.core.usage.change event
"""

YOVA_CORE_USAGE_CHANGE = {
    "type": "object",
    "properties": {
        "cost": {
            "type": "number",
            "minimum": 0,
            "description": "The cost of the operation in USD"
        },
        "daily_cost": {
            "type": "number",
            "minimum": 0,
            "description": "The total daily cost of all operations in USD"
        },
        "daily_budget": {
            "type": "number",
            "minimum": 0,
            "description": "The daily budget for the operation in USD. When 0.00, the budget is unlimited"
        },
        "extra_data": {
            "type": "object",
            "description": "Optional data about the operation to be stored in the usage log"
        }
    },
    "required": ["cost", "daily_cost", "daily_budget"],
    "additionalProperties": False
}
