import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from yova_api_openai.openai_connector import OpenAIConnector


class TestOpenAIConnector:
    
    @pytest.fixture
    def connector(self):
        return OpenAIConnector()
    
    @pytest.fixture
    def mock_openai_client(self):
        with patch('yova_api_openai.openai_connector.AsyncOpenAI') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_configure_with_api_key_in_config(self, connector):
        """Test configuring with API key in config."""
        config = {"api_key": "test-api-key"}
        await connector.configure(config)
        assert connector.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_configure_with_environment_variable(self, connector):
        """Test configuring with API key from environment variable."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-api-key'}):
            config = {}
            await connector.configure(config)
            assert connector.api_key == "env-api-key"
    
    @pytest.mark.asyncio
    async def test_configure_without_api_key(self, connector):
        """Test configuring without API key raises error."""
        with patch.dict('os.environ', {}, clear=True):
            config = {}
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                await connector.configure(config)
    
    @pytest.mark.asyncio
    async def test_configure_with_custom_parameters(self, connector):
        """Test configuring with custom parameters."""
        config = {
            "api_key": "test-key",
            "model": "gpt-4o-mini",
            "system_prompt": "You are a test assistant.",
            "max_tokens": 500,
            "temperature": 0.5
        }
        await connector.configure(config)
        assert connector.model == "gpt-4o-mini"
        assert connector.system_prompt == "You are a test assistant."
        assert connector.max_tokens == 500
        assert connector.temperature == 0.5
    
    @pytest.mark.asyncio
    async def test_connect_success(self, connector, mock_openai_client):
        """Test successful connection."""
        connector.api_key = "test-key"
        await connector.connect()
        assert connector.is_connected is True
        mock_openai_client.assert_called_once_with(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_connect_without_api_key(self, connector):
        """Test connection without API key raises error."""
        with pytest.raises(ConnectionError, match="OpenAI API key not configured"):
            await connector.connect()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, connector, mock_openai_client):
        """Test connection failure."""
        connector.api_key = "test-key"
        mock_openai_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(ConnectionError, match="Failed to connect to OpenAI API"):
            await connector.connect()
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, connector, mock_openai_client):
        """Test successful message sending with streaming."""
        # Setup
        connector.api_key = "test-key"
        connector.is_connected = True
        connector.client = mock_openai_client.return_value
        
        # Mock the streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello"
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = " world"
        
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta.content = None
        
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]
        
        connector.client.chat.completions.create = AsyncMock(return_value=mock_stream)
        
        # Mock event emitter
        connector.event_emitter.emit_event = AsyncMock()
        
        # Execute
        result = await connector.send_message("Test message")
        
        # Verify
        assert result == "Hello world"
        connector.client.chat.completions.create.assert_called_once()
        
        # Verify events were emitted
        assert connector.event_emitter.emit_event.call_count == 3
        
        # Get all calls to verify the structure
        calls = connector.event_emitter.emit_event.call_args_list
        
        # Verify chunk events
        chunk_calls = [call for call in calls if call[0][0] == "message_chunk"]
        assert len(chunk_calls) == 2
        
        # Verify completion event
        completion_calls = [call for call in calls if call[0][0] == "message_completed"]
        assert len(completion_calls) == 1
        
        # Verify all events have the expected structure
        for call in calls:
            event_data = call[0][1]
            assert "id" in event_data
            assert "text" in event_data
        
        # Verify same ID for correlation
        message_id = chunk_calls[0][0][1]["id"]
        assert chunk_calls[1][0][1]["id"] == message_id
        assert completion_calls[0][0][1]["id"] == message_id
        
        # Verify text content
        assert chunk_calls[0][0][1]["text"] == "Hello"
        assert chunk_calls[1][0][1]["text"] == " world"
        assert completion_calls[0][0][1]["text"] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, connector):
        """Test sending message without connection raises error."""
        with pytest.raises(ConnectionError, match="Not connected to OpenAI API"):
            await connector.send_message("Test message")
    
    @pytest.mark.asyncio
    async def test_send_empty_message(self, connector):
        """Test sending empty message returns empty string."""
        connector.is_connected = True
        connector.client = MagicMock()  # Mock the client
        result = await connector.send_message("")
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_send_whitespace_message(self, connector):
        """Test sending whitespace-only message returns empty string."""
        connector.is_connected = True
        connector.client = MagicMock()  # Mock the client
        result = await connector.send_message("   ")
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, connector, mock_openai_client):
        """Test sending message with API error."""
        connector.api_key = "test-key"
        connector.is_connected = True
        connector.client = mock_openai_client.return_value
        connector.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        with pytest.raises(ConnectionError, match="Failed to send message to OpenAI"):
            await connector.send_message("Test message")
    
    def test_event_listener_management(self, connector):
        """Test event listener management methods."""
        mock_listener = MagicMock()
        
        # Mock the event emitter methods
        connector.event_emitter.add_event_listener = MagicMock()
        connector.event_emitter.remove_event_listener = MagicMock()
        connector.event_emitter.clear_event_listeners = MagicMock()
        
        # Test adding listener
        connector.add_event_listener("test_event", mock_listener)
        connector.event_emitter.add_event_listener.assert_called_once_with("test_event", mock_listener)
        
        # Test removing listener
        connector.remove_event_listener("test_event", mock_listener)
        connector.event_emitter.remove_event_listener.assert_called_once_with("test_event", mock_listener)
        
        # Test clearing listeners
        connector.clear_event_listeners("test_event")
        connector.event_emitter.clear_event_listeners.assert_called_once_with("test_event") 