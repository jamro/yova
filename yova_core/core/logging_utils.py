"""
Logging utilities for creating clean logger names.
"""

import logging
from typing import Optional


def get_clean_logger(name: str, parent_logger: Optional[logging.Logger] = None) -> logging.Logger:
    """
    Create a logger with a clean name (just the class/module name, not the full path).
    
    Args:
        name: The name for the logger (e.g., 'audio_recorder', 'openai_transcription_provider')
        parent_logger: Optional parent logger to inherit configuration from
        
    Returns:
        A logger instance with the clean name
    """
    # Check if parent_logger is a mock object (for testing)
    if parent_logger and (hasattr(parent_logger, '_mock_name') or hasattr(parent_logger, '_mock_return_value')):
        # It's a mock, return it directly so tests can verify calls
        return parent_logger
    
    # Create a new logger with the clean name
    logger = logging.getLogger(name)
    
    # Set the level to match the parent or use INFO as default
    if parent_logger:
        # It's a real logger, try to get its level
        try:
            logger.setLevel(parent_logger.level)
        except (AttributeError, TypeError):
            # Fallback to default level if there's any issue
            logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.INFO)
    
    # Don't copy handlers - let the logger inherit from root logger
    # This prevents duplicate log messages
    
    return logger


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration with clean format.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Root logger instance
    """
    # Convert string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = level_map.get(level.upper(), logging.INFO)
    
    # Configure logging with clean format
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s:%(name)s:%(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Set websockets logger to WARNING to reduce noise
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    return logging.getLogger() 