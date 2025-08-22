from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
from yova_shared import get_clean_logger


@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    message_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for OpenAI API."""
        return {
            "role": self.role,
            "content": self.content
        }

    def to_json(self) -> str:
        """Convert message to JSON string for storage."""
        return json.dumps({
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "metadata": self.metadata or {}
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for OpenAI API."""
        return {
            "role": self.role,
            "content": self.content
        }

    def to_serializable_dict(self) -> Dict[str, Any]:
        """Convert message to serializable dictionary for JSON export."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "metadata": self.metadata or {}
        }


class ConversationHistory:
    """
    Manages conversation history with a sliding window approach.
    
    This class maintains a fixed-size conversation history by removing
    older messages when the maximum size is exceeded, ensuring efficient
    memory usage while preserving recent context.
    """
    
    def __init__(self, max_messages: int = 50, max_tokens: int = 4000, logger=None):
        """
        Initialize the conversation history manager.
        
        Args:
            max_messages: Maximum number of messages to keep in history
            max_tokens: Maximum total tokens to keep in history
            logger: Optional logger instance
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.logger = get_clean_logger("conversation_history", logger)
        
        self.messages: List[ConversationMessage] = []
        self.total_tokens = 0
        
        self.logger.info(f"ConversationHistory: Initialized with max_messages={max_messages}, max_tokens={max_tokens}")

    def add_message(self, role: str, content: str, message_id: Optional[str] = None, 
                   metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """
        Add a new message to the conversation history.
        
        Args:
            role: Role of the message sender ("user" or "assistant")
            content: Content of the message
            message_id: Optional unique identifier for the message
            metadata: Optional additional data about the message
            
        Returns:
            The created ConversationMessage instance
        """
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            message_id=message_id,
            metadata=metadata
        )
        
        self.messages.append(message)
        self._estimate_tokens(content)
        self._trim_history()
        
        self.logger.debug(f"Added message: role={role}, content_length={len(content)}, total_messages={len(self.messages)}")
        return message

    def add_user_message(self, content: str, message_id: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """Add a user message to the conversation."""
        return self.add_message("user", content, message_id, metadata)

    def add_assistant_message(self, content: str, message_id: Optional[str] = None, 
                            metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """Add an assistant message to the conversation."""
        return self.add_message("assistant", content, message_id, metadata)

    def get_messages_for_api(self, include_system: bool = True, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get messages in the format expected by OpenAI API.
        
        Args:
            include_system: Whether to include system message at the beginning
            system_prompt: System prompt to include if include_system is True
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        api_messages = []
        
        if include_system and system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        
        # Convert conversation messages to API format
        for message in self.messages:
            api_messages.append(message.to_dict())
        
        return api_messages

    def get_recent_messages(self, count: int) -> List[ConversationMessage]:
        """Get the most recent messages from the conversation."""
        return self.messages[-count:] if count > 0 else []

    def get_messages_by_role(self, role: str) -> List[ConversationMessage]:
        """Get all messages from a specific role."""
        return [msg for msg in self.messages if msg.role == role]

    def get_message_by_id(self, message_id: str) -> Optional[ConversationMessage]:
        """Find a message by its ID."""
        for message in self.messages:
            if message.message_id == message_id:
                return message
        return None

    def clear_history(self):
        """Clear all conversation history."""
        self.messages.clear()
        self.total_tokens = 0
        self.logger.info("ConversationHistory: Cleared all conversation history")

    def remove_message(self, message_id: str) -> bool:
        """
        Remove a specific message by ID.
        
        Returns:
            True if message was found and removed, False otherwise
        """
        for i, message in enumerate(self.messages):
            if message.message_id == message_id:
                removed_message = self.messages.pop(i)
                self._estimate_tokens(removed_message.content, remove=True)
                self.logger.debug(f"Removed message with ID: {message_id}")
                return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current conversation."""
        user_messages = len([msg for msg in self.messages if msg.role == "user"])
        assistant_messages = len([msg for msg in self.messages if msg.role == "assistant"])
        
        return {
            "total_messages": len(self.messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "estimated_tokens": self.total_tokens,
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens,
            "first_message_time": self.messages[0].timestamp.isoformat() if self.messages else None,
            "last_message_time": self.messages[-1].timestamp.isoformat() if self.messages else None
        }

    def export_history(self, format_type: str = "json") -> str:
        """
        Export conversation history in specified format.
        
        Args:
            format_type: Export format ("json" or "text")
            
        Returns:
            Exported conversation history as string
        """
        if format_type == "json":
            return json.dumps({
                "conversation": [msg.to_serializable_dict() for msg in self.messages],
                "statistics": self.get_statistics()
            }, indent=2)
        elif format_type == "text":
            lines = ["Conversation History", "=" * 20, ""]
            for msg in self.messages:
                lines.append(f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {msg.role.upper()}:")
                lines.append(f"{msg.content}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _estimate_tokens(self, text: str, remove: bool = False):
        """
        Estimate token count for text and update total.
        This is a rough estimation - OpenAI's actual tokenization may differ.
        
        Args:
            text: Text to estimate tokens for
            remove: If True, subtract tokens instead of adding
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        estimated_tokens = len(text) // 4
        
        if remove:
            self.total_tokens = max(0, self.total_tokens - estimated_tokens)
        else:
            self.total_tokens += estimated_tokens

    def _trim_history(self):
        """Trim history to stay within limits."""
        # Trim by message count
        while len(self.messages) > self.max_messages:
            removed_message = self.messages.pop(0)
            self._estimate_tokens(removed_message.content, remove=True)
            self.logger.debug(f"Trimmed message due to max_messages limit: {removed_message.role}")

        # Trim by token count (if we have a more accurate token count)
        # This is a simplified approach - in production you might want to use
        # OpenAI's tokenizer for more accurate counting
        while self.total_tokens > self.max_tokens and len(self.messages) > 1:
            removed_message = self.messages.pop(0)
            self._estimate_tokens(removed_message.content, remove=True)
            self.logger.debug(f"Trimmed message due to max_tokens limit: {removed_message.role}")

    def __len__(self) -> int:
        """Return the number of messages in the conversation."""
        return len(self.messages)

    def __str__(self) -> str:
        """String representation of the conversation history."""
        stats = self.get_statistics()
        return f"ConversationHistory(messages={stats['total_messages']}, tokens={stats['estimated_tokens']})"
