from .yova_core_health_ping import YOVA_CORE_HEALTH_PING

ALL_EVENTS = {
  'YOVA_CORE_HEALTH_PING': YOVA_CORE_HEALTH_PING
}

ENVELOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "v": {
            "type": "integer",
            "const": 1,
            "description": "Version number for the envelope format"
        },
        "event": {
            "type": "string",
            "pattern": "^yova\\.[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*$",
            "description": "The event topic/path that matches the ZeroMQ topic"
        },
        "msg_id": {
            "type": "string",
            "minLength": 1,
            "pattern": "^\\S+$",
            "description": "Unique identifier for each message (any non-empty text without whitespace)"
        },
        "source": {
            "type": "string",
            "minLength": 1,
            "description": "Name of the module that published the event"
        },
        "ts_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Unix timestamp in milliseconds when the event was created"
        },
        "data": {
            "type": "object",
            "description": "Event-specific payload containing the actual event data"
        }
    },
    "required": ["v", "event", "msg_id", "source", "ts_ms", "data"],
    "additionalProperties": False
}