"""Integration tests for the EventEmitter class demonstrating practical usage."""

import pytest
import asyncio
from unittest.mock import Mock
from yova_core.core.event_emitter import EventEmitter


class TestEventEmitterIntegration:
    """Integration tests demonstrating practical EventEmitter usage."""

    @pytest.mark.asyncio
    async def test_yova_scenario(self):
        """Test a realistic voice command scenario with multiple listeners."""
        emitter = EventEmitter()
        results = []

        # Simulate different components listening to voice commands
        async def speech_processor(data):
            results.append(f"speech_processed: {data['text']}")

        async def command_parser(data):
            results.append(f"command_parsed: {data['text'].upper()}")

        async def response_generator(data):
            results.append(f"response_generated: Hello, I heard '{data['text']}'")

        # Register listeners
        emitter.add_event_listener("yova", speech_processor)
        emitter.add_event_listener("yova", command_parser)
        emitter.add_event_listener("yova", response_generator)

        # Emit a voice command event
        await emitter.emit_event("yova", {"text": "turn on the lights"})

        # Verify all listeners were called
        assert len(results) == 3
        assert "speech_processed: turn on the lights" in results
        assert "command_parsed: TURN ON THE LIGHTS" in results
        assert "response_generated: Hello, I heard 'turn on the lights'" in results

    @pytest.mark.asyncio
    async def test_error_handling_scenario(self):
        """Test error handling when listeners fail."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)
        results = []

        async def working_listener(data):
            results.append("working")

        async def failing_listener(data):
            raise RuntimeError("Simulated failure")

        # Register both working and failing listeners
        emitter.add_event_listener("test_event", working_listener)
        emitter.add_event_listener("test_event", failing_listener)

        # Emit event - should not raise exception
        await emitter.emit_event("test_event", {"data": "test"})

        # Verify working listener was called
        assert len(results) == 1
        assert results[0] == "working"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Error in event listener for 'test_event'" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_dynamic_listener_management(self):
        """Test adding and removing listeners dynamically."""
        emitter = EventEmitter()
        results = []

        async def listener1(data):
            results.append("listener1")

        async def listener2(data):
            results.append("listener2")

        # Start with one listener
        emitter.add_event_listener("dynamic_event", listener1)
        assert emitter.get_listener_count("dynamic_event") == 1

        # Add second listener
        emitter.add_event_listener("dynamic_event", listener2)
        assert emitter.get_listener_count("dynamic_event") == 2

        # Emit event with both listeners
        await emitter.emit_event("dynamic_event", {"data": "test"})
        assert len(results) == 2
        assert "listener1" in results
        assert "listener2" in results

        # Remove first listener
        emitter.remove_event_listener("dynamic_event", listener1)
        assert emitter.get_listener_count("dynamic_event") == 1

        # Clear results and emit again
        results.clear()
        await emitter.emit_event("dynamic_event", {"data": "test"})
        assert len(results) == 1
        assert results[0] == "listener2"

    @pytest.mark.asyncio
    async def test_multiple_event_types(self):
        """Test handling multiple different event types."""
        emitter = EventEmitter()
        voice_results = []
        system_results = []

        async def voice_handler(data):
            voice_results.append(data["message"])

        async def system_handler(data):
            system_results.append(data["status"])

        # Register listeners for different event types
        emitter.add_event_listener("yova", voice_handler)
        emitter.add_event_listener("system_status", system_handler)

        # Emit different types of events
        await emitter.emit_event("yova", {"message": "Hello world"})
        await emitter.emit_event("system_status", {"status": "online"})
        await emitter.emit_event("yova", {"message": "Goodbye"})

        # Verify results
        assert voice_results == ["Hello world", "Goodbye"]
        assert system_results == ["online"]

        # Verify event type tracking
        event_types = emitter.get_all_event_types()
        assert len(event_types) == 2
        assert "yova" in event_types
        assert "system_status" in event_types

    @pytest.mark.asyncio
    async def test_listener_cleanup_scenario(self):
        """Test cleanup scenarios for listeners."""
        emitter = EventEmitter()
        results = []

        async def temp_listener(data):
            results.append("temp")

        async def permanent_listener(data):
            results.append("permanent")

        # Add both listeners
        emitter.add_event_listener("cleanup_test", temp_listener)
        emitter.add_event_listener("cleanup_test", permanent_listener)

        # Emit event
        await emitter.emit_event("cleanup_test", {"data": "test"})
        assert len(results) == 2

        # Clear temporary listener
        emitter.remove_event_listener("cleanup_test", temp_listener)
        results.clear()

        # Emit again - only permanent listener should respond
        await emitter.emit_event("cleanup_test", {"data": "test"})
        assert len(results) == 1
        assert results[0] == "permanent"

        # Clear all listeners
        emitter.clear_event_listeners("cleanup_test")
        results.clear()

        # Emit again - no listeners should respond
        await emitter.emit_event("cleanup_test", {"data": "test"})
        assert len(results) == 0

    def test_logger_integration(self):
        """Test logger integration throughout the lifecycle."""
        mock_logger = Mock()
        emitter = EventEmitter(logger=mock_logger)

        # Test logger calls during add/remove operations
        async def test_listener(data):
            pass

        emitter.add_event_listener("logger_test", test_listener)
        mock_logger.debug.assert_called_with("Added event listener for 'logger_test'")

        emitter.remove_event_listener("logger_test", test_listener)
        mock_logger.debug.assert_any_call("Removed event listener for 'logger_test'")

        emitter.clear_event_listeners("logger_test")
        mock_logger.debug.assert_any_call("Cleared all listeners for 'logger_test'")


if __name__ == "__main__":
    pytest.main([__file__]) 