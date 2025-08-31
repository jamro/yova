# Simplified Speaker Verification System

This module provides speaker verification capabilities using ECAPA embeddings with a clean, focused API.

## Features

- **Simple Enrollment**: Add speakers with their audio embeddings
- **Basic Verification**: Verify speakers using cosine similarity
- **Speaker Identification**: Identify speakers from enrolled set
- **Clean API**: Simple, focused interface

## Key Classes

### SpeakerVerifier

The main class for speaker verification.

#### Initialization

```python
from yova_core.voice_id.speaker_verifier import SpeakerVerifier

# Initialize with threshold
verifier = SpeakerVerifier(similarity_threshold=0.2868)
```

#### Enrollment

```python
# Add a speaker sample
verifier.enroll_speaker("user_123", embedding1)

# Add more samples for the same speaker
verifier.enroll_speaker("user_123", embedding2)
verifier.enroll_speaker("user_123", embedding3)
```

#### Verification

```python
# Verify a test embedding against a speaker
is_match, similarity, confidence_level, confidence_score = verifier.verify_speaker(
    test_embedding, "user_123"
)

print(f"Match: {is_match}")
print(f"Similarity: {similarity:.4f}")
print(f"Confidence: {confidence_level}")
```

#### Speaker Identification

```python
# Identify the most likely speaker from all enrolled speakers
identified_speaker, similarity, confidence_level, confidence_score = verifier.identify_speaker(
    test_embedding
)
```

## Best Practices

### 1. Sample Collection

- **Multiple Samples**: Record 3-5 samples per speaker
- **Different Conditions**: Vary recording environment and content
- **Quality**: Ensure clear audio with minimal noise

### 2. Threshold Tuning

The default threshold (0.2868) is optimized for ECAPA embeddings:

- **High Security**: Use 0.6+ (fewer false positives)
- **Balanced**: Use 0.2868 (optimal F1 score)
- **High Recall**: Use 0.2- (fewer false negatives)

## Example Usage

```python
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
import numpy as np

# Initialize verifier
verifier = SpeakerVerifier()

# Enroll speakers
verifier.enroll_speaker("alice", embedding1)
verifier.enroll_speaker("alice", embedding2)
verifier.enroll_speaker("bob", embedding3)

# Check enrollment
print(f"Alice samples: {verifier.get_speaker_sample_count('alice')}")
print(f"Bob samples: {verifier.get_speaker_sample_count('bob')}")

# Verify speakers
test_embedding = np.random.randn(192)  # Your test embedding
is_match, similarity, confidence, _ = verifier.verify_speaker(test_embedding, "alice")

# Get enrolled speakers
enrolled = verifier.get_enrolled_speakers()
print(f"Enrolled speakers: {enrolled}")
```

## API Reference

### Core Methods

- `enroll_speaker(speaker_id, embedding)` - Add single sample
- `verify_speaker(test_embedding, speaker_id)` - Verify against specific speaker
- `identify_speaker(test_embedding)` - Identify from all enrolled speakers

### Utility Methods

- `get_speaker_sample_count(speaker_id)` - Get sample count for speaker
- `get_enrolled_speakers()` - Get list of enrolled speaker IDs
- `remove_speaker_sample(speaker_id, index)` - Remove specific sample
- `clear_speaker(speaker_id)` - Remove all samples for a speaker

### Data Structures

- `enrolled_speakers`: Dict[str, List[np.ndarray]] - Speaker ID to list of embeddings
- `similarity_threshold`: float - Verification threshold
