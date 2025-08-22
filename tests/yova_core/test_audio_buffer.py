#!/usr/bin/env python3

"""Tests for the AudioBuffer class."""

import pytest
import time
from unittest.mock import Mock
from yova_core.speech2text.audio_buffer import AudioBuffer

class TestAudioBuffer:
    """Test cases for the AudioBuffer class."""
    
    def test_initialization(self):
        """Test AudioBuffer initialization."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        assert buffer.logger == mock_logger
        assert buffer.sample_rate == 16000
        assert buffer.audio_channels == 1
        assert buffer.max_age_threshold == 30.0
        assert buffer.get_buffer_size() == 0
        assert buffer.get_total_buffered_length() == 0.0
        assert not buffer.has_buffered_audio()
    
    def test_initialization_with_custom_params(self):
        """Test AudioBuffer initialization with custom parameters."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, sample_rate=44100, audio_channels=2, max_age_threshold=60.0)
        
        assert buffer.sample_rate == 44100
        assert buffer.audio_channels == 2
        assert buffer.max_age_threshold == 60.0
    
    def test_add_audio_chunk(self):
        """Test adding audio chunks to the buffer."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        # Add a simple audio chunk (6 bytes = 3 int16 values)
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        
        assert buffer.get_buffer_size() == 1
        assert buffer.has_buffered_audio() is True
        assert len(buffer.get_buffered_chunks()) == 1
        assert buffer.get_buffered_chunks()[0] == audio_chunk
        
        # Verify logging was called
        mock_logger.info.assert_called_once()
    
    def test_get_buffered_chunks_with_timestamps(self):
        """Test getting buffered audio chunks with timestamps."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        
        chunks_with_timestamps = buffer.get_buffered_chunks_with_timestamps()
        assert len(chunks_with_timestamps) == 1
        
        timestamp, chunk = chunks_with_timestamps[0]
        assert chunk == audio_chunk
        assert isinstance(timestamp, float)
        assert timestamp > 0
    
    def test_get_buffered_audio_info(self):
        """Test getting buffered audio information."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        # Initially empty
        info = buffer.get_buffered_audio_info()
        assert info['chunk_count'] == 0
        assert info['total_length'] == 0.0
        assert info['is_empty'] is True
        assert info['max_age_threshold'] == 30.0
        assert info['oldest_chunk_age'] == 0.0
        assert info['newest_chunk_age'] == 0.0
        
        # Add some audio chunks
        audio_chunk1 = b"\x00\x00\x01\x00\x02\x00"  # 6 bytes
        audio_chunk2 = b"\x03\x00\x04\x00"  # 4 bytes
        buffer.add_audio_chunk(audio_chunk1)
        buffer.add_audio_chunk(audio_chunk2)
        
        info = buffer.get_buffered_audio_info()
        assert info['chunk_count'] == 2
        assert info['total_length'] > 0.0
        assert info['is_empty'] is False
        assert info['max_age_threshold'] == 30.0
        assert info['oldest_chunk_age'] >= 0.0
        assert info['newest_chunk_age'] >= 0.0
    
    def test_clear_buffer(self):
        """Test clearing the buffer."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        # Add some audio chunks
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        assert buffer.has_buffered_audio() is True
        
        # Clear the buffer
        buffer.clear_buffer()
        
        assert buffer.get_buffer_size() == 0
        assert buffer.get_total_buffered_length() == 0.0
        assert not buffer.has_buffered_audio()
        assert len(buffer.get_buffered_chunks()) == 0
        
        # Verify logging was called
        mock_logger.info.assert_called_with("Audio chunk buffer cleared")
    
    def test_get_buffered_chunks_copy(self):
        """Test that get_buffered_chunks returns a copy, not the original list."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        
        chunks = buffer.get_buffered_chunks()
        chunks.append(b"extra_chunk")  # Modify the returned list
        
        # Original buffer should be unchanged
        assert buffer.get_buffer_size() == 1
        assert len(buffer.get_buffered_chunks()) == 1
    
    def test_audio_length_calculation(self):
        """Test audio length calculation."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, sample_rate=16000, audio_channels=1)
        
        # 6 bytes = 3 int16 values = 3 samples
        # 3 samples / (16000 Hz * 1 channel) = 0.0001875 seconds
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        
        expected_length = 3 / (16000 * 1)  # 0.0001875 seconds
        assert abs(buffer.get_total_buffered_length() - expected_length) < 0.0001
    
    def test_empty_audio_chunk(self):
        """Test handling of empty audio chunks."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        # Empty chunk
        buffer.add_audio_chunk(b"")
        assert buffer.get_buffer_size() == 1
        assert buffer.get_total_buffered_length() == 0.0
        
        # None chunk
        buffer.add_audio_chunk(None)
        assert buffer.get_buffer_size() == 2
        assert buffer.get_total_buffered_length() == 0.0
    
    def test_age_threshold_functionality(self):
        """Test that old chunks are automatically removed based on age threshold."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, max_age_threshold=0.1)  # 100ms threshold
        
        # Add a chunk
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        assert buffer.get_buffer_size() == 1
        
        # Wait for chunk to become old
        time.sleep(0.2)
        
        # Check that old chunk is automatically removed
        assert buffer.get_buffer_size() == 0
        assert not buffer.has_buffered_audio()
    
    def test_set_max_age_threshold(self):
        """Test setting the maximum age threshold."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, max_age_threshold=30.0)
        
        assert buffer.get_max_age_threshold() == 30.0
        
        # Change threshold
        buffer.set_max_age_threshold(60.0)
        assert buffer.get_max_age_threshold() == 60.0
        
        # Verify logging was called
        mock_logger.info.assert_called_with("Updated max age threshold from 30.0s to 60.0s")
    
    def test_set_max_age_threshold_invalid(self):
        """Test setting invalid age threshold."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger)
        
        with pytest.raises(ValueError, match="Age threshold must be non-negative"):
            buffer.set_max_age_threshold(-1.0)
    
    def test_age_threshold_cleanup_on_threshold_change(self):
        """Test that changing threshold triggers cleanup of old chunks."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, max_age_threshold=1.0)  # 1 second threshold
        
        # Add a chunk
        audio_chunk = b"\x00\x00\x01\x00\x02\x00"
        buffer.add_audio_chunk(audio_chunk)
        assert buffer.get_buffer_size() == 1
        
        # Wait a bit but not enough to exceed current threshold
        time.sleep(0.5)
        assert buffer.get_buffer_size() == 1
        
        # Reduce threshold to trigger cleanup
        buffer.set_max_age_threshold(0.1)  # 100ms threshold
        
        # Chunk should now be considered old and removed
        assert buffer.get_buffer_size() == 0
    
    def test_multiple_chunks_with_different_ages(self):
        """Test handling of multiple chunks with different ages."""
        mock_logger = Mock()
        buffer = AudioBuffer(mock_logger, max_age_threshold=0.5)  # 500ms threshold
        
        # Add first chunk
        audio_chunk1 = b"\x00\x00\x01\x00"
        buffer.add_audio_chunk(audio_chunk1)
        assert buffer.get_buffer_size() == 1
        
        # Wait a bit
        time.sleep(0.2)
        
        # Add second chunk
        audio_chunk2 = b"\x02\x00\x03\x00"
        buffer.add_audio_chunk(audio_chunk2)
        assert buffer.get_buffer_size() == 2
        
        # Wait for first chunk to become old
        time.sleep(0.4)
        
        # First chunk should be removed, second should remain
        assert buffer.get_buffer_size() == 1
        chunks = buffer.get_buffered_chunks()
        assert chunks[0] == audio_chunk2
