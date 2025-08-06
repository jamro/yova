"""Main application module for Voice Command Station."""

import sys
from typing import Optional
from voice_command_station.speech2text import AudioRecorder

def hello_world(name: Optional[str] = None) -> str:
    """
    Return a hello world message.
    
    Args:
        name: Optional name to greet. If None, uses "World".
        
    Returns:
        A greeting message.
    """
    if name is None:
        name = "World"
    return f"Hello, {name}! Welcome to Voice Command Station!"


def main():
    """Main entry point for the application."""
    # Get name from command line arguments if provided
    name = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Print the hello world message
    message = hello_world(name)
    print(message)
    
    # Additional welcome information
    print(f"Version: {__import__('voice_command_station').__version__}")
    print("Ready to process voice commands!")


if __name__ == "__main__":
    main() 