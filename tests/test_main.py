"""Tests for the main module."""

import pytest
from voice_command_station.main import hello_world


def test_hello_world_default():
    """Test hello_world function with default parameter."""
    result = hello_world()
    assert result == "Hello, World! Welcome to Voice Command Station!"


def test_hello_world_with_name():
    """Test hello_world function with a specific name."""
    result = hello_world("Alice")
    assert result == "Hello, Alice! Welcome to Voice Command Station!"


def test_hello_world_with_empty_string():
    """Test hello_world function with empty string."""
    result = hello_world("")
    assert result == "Hello, ! Welcome to Voice Command Station!"


if __name__ == "__main__":
    pytest.main([__file__]) 