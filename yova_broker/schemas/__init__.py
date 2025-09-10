from .yova_core_health_ping import YOVA_CORE_HEALTH_PING
from .yova_api_asr_result import YOVA_API_ASR_RESULT
from .yova_api_tts_chunk import YOVA_API_TTS_CHUNK
from .yova_api_tts_complete import YOVA_API_TTS_COMPLETE
from .yova_api_thinking_start import YOVA_API_THINKING_START
from .yova_api_thinking_stop import YOVA_API_THINKING_STOP
from .yova_api_usage_occur import YOVA_API_USAGE_OCCUR
from .yova_api_error import YOVA_API_ERROR
from .yova_core_state_change import YOVA_CORE_STATE_CHANGE
from .yova_core_usage_change import YOVA_CORE_USAGE_CHANGE
from .yova_core_audio_record_start import YOVA_CORE_AUDIO_RECORD_START
from .yova_core_audio_play_start import YOVA_CORE_AUDIO_PLAY_START
from .yova_core_input_state import YOVA_CORE_INPUT_STATE
from .yova_core_error import YOVA_CORE_ERROR

ALL_EVENTS = {
    'YOVA_CORE_HEALTH_PING': YOVA_CORE_HEALTH_PING,
    'YOVA_API_ASR_RESULT': YOVA_API_ASR_RESULT,
    'YOVA_API_TTS_CHUNK': YOVA_API_TTS_CHUNK,
    'YOVA_API_TTS_COMPLETE': YOVA_API_TTS_COMPLETE,
    'YOVA_API_THINKING_START': YOVA_API_THINKING_START,
    'YOVA_API_THINKING_STOP': YOVA_API_THINKING_STOP,
    'YOVA_API_USAGE_OCCUR': YOVA_API_USAGE_OCCUR,
    'YOVA_API_ERROR': YOVA_API_ERROR,
    'YOVA_CORE_STATE_CHANGE': YOVA_CORE_STATE_CHANGE,
    'YOVA_CORE_USAGE_CHANGE': YOVA_CORE_USAGE_CHANGE,
    'YOVA_CORE_AUDIO_RECORD_START': YOVA_CORE_AUDIO_RECORD_START,
    'YOVA_CORE_AUDIO_PLAY_START': YOVA_CORE_AUDIO_PLAY_START,
    'YOVA_CORE_INPUT_STATE': YOVA_CORE_INPUT_STATE,
    'YOVA_CORE_ERROR': YOVA_CORE_ERROR
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