# Speaker Verification with Ensemble Averaging

This module provides speaker verification capabilities using ECAPA embeddings with support for ensemble averaging from multiple audio samples.

## Features

- **Ensemble Averaging**: Combine multiple audio samples for robust speaker recognition
- **Progressive Enrollment**: Add samples incrementally to improve speaker models
- **Quality Metrics**: Track consistency and variance across samples
- **Flexible Sample Management**: Add, remove, and manage individual samples

## Key Classes

### SpeakerVerifier

The main class for speaker verification with ensemble averaging support.

#### Initialization

```python
from yova_core.voice_id.speaker_verifier import SpeakerVerifier

# Initialize with optimal threshold
verifier = SpeakerVerifier(similarity_threshold=0.2868)
```

#### Enrollment Methods

##### 1. Progressive Enrollment (Recommended for Real-time)

Add samples one by one as they become available:

```python
# Add first sample
verifier.enroll_speaker("user_123", embedding1)

# Add more samples later
verifier.enroll_speaker("user_123", embedding2)
verifier.enroll_speifier("user_123", embedding3)

# Speaker now has 3 samples automatically averaged
```

##### 2. Ensemble Enrollment

Provide all samples at once for immediate averaging:

```python
# Collect multiple samples first
embeddings = [embedding1, embedding2, embedding3]

# Enroll with ensemble averaging
verifier.enroll_speaker_ensemble("user_123", embeddings)
```

#### Verification

```python
# Verify a test embedding against a speaker
is_match, similarity, confidence_level, confidence_score = verifier.verify_speaker(
    test_embedding, "user_123"
)

print(f"Match: {is_match}")
print(f"Similarity: {similarity:.4f}")
print(f"Confidence: {confidence_level} ({confidence_score:.4f})")
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

- **Multiple Environments**: Record samples in different acoustic conditions
- **Varying Content**: Use different phrases/sentences
- **Quality Variation**: Include samples with different noise levels
- **Duration**: Aim for 3-10 seconds per sample

### 2. Enrollment Strategy

- **Start with 3-5 samples** for initial enrollment
- **Add samples progressively** as more audio becomes available
- **Monitor consistency scores** to ensure quality
- **Remove poor quality samples** if they hurt performance

### 3. Threshold Tuning

The default threshold (0.2868) is optimized for ECAPA embeddings:

- **High Security**: Use 0.6+ (fewer false positives, more false negatives)
- **Balanced**: Use 0.2868 (optimal F1 score)
- **High Recall**: Use 0.2- (more false positives, fewer false negatives)

## Example Usage

```python
from yova_core.voice_id.speaker_verifier import SpeakerVerifier
import numpy as np

# Initialize verifier
verifier = SpeakerVerifier()

# Method 1: Progressive enrollment
verifier.enroll_speaker("alice", embedding1)
verifier.enroll_speaker("alice", embedding2)
verifier.enroll_speaker("alice", embedding3)

# Method 2: Ensemble enrollment
verifier.enroll_speaker_ensemble("bob", [embedding4, embedding5, embedding6])

# Check enrollment status
print(f"Alice samples: {verifier.get_speaker_sample_count('alice')}")
print(f"Bob samples: {verifier.get_speaker_sample_count('bob')}")

# Verify speakers
test_embedding = np.random.randn(192)  # Your test embedding
is_match, similarity, confidence, conf_score = verifier.verify_speaker(test_embedding, "alice")

# Get statistics
stats = verifier.get_speaker_statistics()
for speaker_id, speaker_stats in stats.items():
    print(f"{speaker_id}: {speaker_stats['sample_count']} samples, "
          f"consistency: {speaker_stats['consistency_score']:.3f}")
```

## Performance Benefits

### 1. Improved Accuracy

- **Reduced Variance**: Multiple samples provide more stable representations
- **Better Generalization**: Covers different recording conditions
- **Robust Recognition**: Less sensitive to individual sample quality

### 2. Confidence Scoring

- **Sample Count**: More samples generally mean higher confidence
- **Consistency Metrics**: Lower variance indicates better quality enrollment
- **Adaptive Thresholds**: Can adjust based on sample count and quality

### 3. Sample Management

- **Quality Control**: Remove poor samples to improve performance
- **Progressive Improvement**: Add samples over time for better models
- **Storage Efficiency**: Store multiple samples per speaker

## Troubleshooting

### Common Issues

1. **Low Similarity Scores**: Ensure embeddings are properly normalized
2. **Poor Recognition**: Check sample quality and consistency
3. **Memory Usage**: Monitor total sample count across speakers

### Debugging

```python
# Get detailed statistics
stats = verifier.get_speaker_statistics()
for speaker_id, speaker_stats in stats.items():
    print(f"Speaker {speaker_id}:")
    print(f"  Samples: {speaker_stats['sample_count']}")
    print(f"  Variance: {speaker_stats['variance']:.6f}")
    print(f"  Consistency: {speaker_stats['consistency_score']:.4f}")

# Check individual samples
speaker_id = "user_123"
sample_count = verifier.get_speaker_sample_count(speaker_id)
print(f"Speaker {speaker_id} has {sample_count} samples")
```

## API Reference

### Core Methods

- `enroll_speaker(speaker_id, embedding)` - Add single sample
- `enroll_speaker_ensemble(speaker_id, embeddings)` - Add multiple samples at once
- `verify_speaker(test_embedding, speaker_id)` - Verify against specific speaker
- `identify_speaker(test_embedding)` - Identify from all enrolled speakers

### Utility Methods

- `get_speaker_sample_count(speaker_id)` - Get sample count for speaker
- `get_speaker_statistics()` - Get detailed statistics for all speakers
- `remove_speaker_sample(speaker_id, index)` - Remove specific sample
- `get_total_samples()` - Get total samples across all speakers

### Data Structures

- `enrolled_speakers`: Dict[str, List[np.ndarray]] - Speaker ID to list of embeddings
- `confidence_thresholds`: Dict[str, float] - Confidence level thresholds
- `similarity_threshold`: float - Verification threshold
