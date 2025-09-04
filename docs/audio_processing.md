# Audio Processing Pipeline for Speech Recognition

Yova voice assistant uses a audio processing pipeline to improve audio quality before sending it to the Automatic Speech Recognition (ASR) system. This pipeline consists of several processing stages that work together to clean and enhance the audio signal.

## Overview

The audio processing pipeline applies multiple filters and enhancements in sequence to transform raw microphone input into clean, optimized audio for speech recognition. Each processor addresses specific audio quality issues commonly found in real-world recording environments.

## Processing Stages

### 1. High-Pass Filter (Speech High-Pass)
**Purpose**: Removes low-frequency rumble and noise below speech frequencies
- **What it does**: Filters out frequencies below 70 Hz (configurable)
- **Why it helps**: Eliminates background rumble, HVAC noise, and other low-frequency interference that can confuse speech recognition
- **Technical details**: Uses a 2nd-order Butterworth high-pass filter

### 2. Declicking
**Purpose**: Removes sudden audio spikes and clicks
- **What it does**: Detects and removes single-sample audio artifacts using statistical analysis
- **Why it helps**: Eliminates digital clicks, pops, and other transient noise that can cause recognition errors
- **Technical details**: Uses median/MAD (Median Absolute Deviation) outlier detection with a 5-sample window

### 3. Noise Suppression
**Purpose**: Reduces background noise while preserving speech
- **What it does**: Uses spectral analysis to identify and reduce noise components
- **Why it helps**: Improves speech clarity in noisy environments (level 2 = moderate suppression by default)
- **Technical details**: 
  - VAD-guided spectral noise suppression
  - Uses FFT analysis with 75% overlap
  - Adapts to different noise levels automatically

### 4. Voice Activity Detection (VAD)
**Purpose**: Identifies when speech is present vs. silence/noise
- **What it does**: Analyzes audio to determine if speech is being spoken
- **Why it helps**: Prevents processing of non-speech audio, improving efficiency and accuracy
- **Technical details**: Uses WebRTC VAD with configurable aggressiveness

### 5. Automatic Gain Control (AGC)
**Purpose**: Automatically adjusts audio volume to consistent levels
- **What it does**: Dynamically amplifies quiet speech and reduces loud speech
- **Why it helps**: Ensures consistent audio levels regardless of speaker distance or volume

### 6. Normalization
**Purpose**: Standardizes audio levels and prevents clipping
- **What it does**: Adjusts overall volume to target levels and limits peak levels
- **Why it helps**: Ensures optimal input levels for speech recognition

### 7. Edge Fade
**Purpose**: Smooths audio boundaries to prevent artifacts
- **What it does**: Applies gentle fade-in and fade-out at audio chunk edges
- **Why it helps**: Prevents clicking and popping sounds at audio boundaries
- **Technical details**: 1ms fade duration at start and end of each audio chunk

## Configuration

The audio processing pipeline is highly configurable through the `yova.config.json` file:
See [config.md](config.md) for more details.

## Benefits for Speech Recognition

This multi-stage processing pipeline provides several key benefits:

1. **Noise Reduction**: Removes background noise and interference
2. **Consistent Levels**: Ensures uniform audio volume regardless of recording conditions
3. **Artifact Removal**: Eliminates clicks, pops, and other audio artifacts
4. **Speech Focus**: Emphasizes speech frequencies while filtering out irrelevant sounds
5. **Boundary Smoothing**: Prevents audio artifacts at chunk boundaries

## Performance Considerations

- **Real-time Processing**: All processors are optimized for real-time operation
- **Low Latency**: Minimal processing delay to maintain responsive voice interaction
- **Memory Efficient**: Uses streaming processing with minimal memory footprint
- **Configurable**: Individual processors can be enabled/disabled based on needs

The result is clean, consistent audio that significantly improves the accuracy and reliability of speech recognition in real-world environments.
