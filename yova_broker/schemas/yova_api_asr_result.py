"""
Schema for yova.api.asr.result event
"""

YOVA_API_ASR_RESULT = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the ASR result"
        },
        "transcript": {
            "type": "string",
            "description": "Transcribed text from voice command"
        },
        "voice_id": {
            "type": ["object", "null"],
            "properties": {
                "user_id": {
                    "type": ["string", "null"],
                    "description": "The ID of the identified user, or null if no user was identified"
                },
                "similarity": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "The similarity score between the recorded audio and the user's voice"
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "The confidence level of the identified user"
                },
                "embedding": {
                    "type": ["object", "null"],
                    "properties": {
                        "embedding_base64": {
                            "type": "string",
                            "description": "Base64 encoded embedding vector"
                        },
                        "embedding_dtype": {
                            "type": "string",
                            "description": "Data type of the embedding vector"
                        },
                        "embedding_shape": {
                            "type": "array",
                            "items": {
                                "type": "number"
                            },
                            "minItems": 1,
                            "description": "Shape of the embedding vector"
                        }
                    },
                    "required": ["embedding_base64", "embedding_dtype", "embedding_shape"],
                    "additionalProperties": False,
                    "description": "Voice embedding data (only included if include_embedding is enabled)"
                }
            },
            "required": ["user_id", "similarity", "confidence_level"],
            "additionalProperties": False,
            "description": "Voice identification data (optional, only included if voice ID is enabled)"
        }
    },
    "required": ["id", "transcript"],
    "additionalProperties": False
}
