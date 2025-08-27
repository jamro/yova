# Performance

## Overview

This document covers Yova's performance characteristics, including current test results and design strategies for optimizing response times and reducing processing lag.

## Current Performance Test Results

### Test Setup

- Test Device: Raspberry Pi 5
- Test Sentence: "What is the capital of France?"
- text2speech model: gpt-4o-mini-tts
- speech2text model: gpt-4o-transcribe

### Timing Definitions

Before presenting the test results, it's important to understand what each timing measurement represents:

- **Input**: Duration from pressing the push-to-talk button to the start of recording
- **Question**: Duration from releasing the push-to-talk button to sending the message to the backend API
- **Answer**: Duration from receiving the first chunk of response from the backend API to the start of playing speech

**Note**: All durations are measured in milliseconds (ms).

### Test Results

| Input | Question | Answer |
|-------|----------|--------|
|   114 |      487 |    695 |
|    55 |      501 |    582 |
|    65 |      546 |    581 |
|    66 |      521 |    459 |
|    68 |      526 |    715 |
|    71 |      603 |    740 |
|    66 |      830 |   1042 |
|    65 |      552 |    573 |
|    60 |      529 |    951 |
|    60 |      634 |    797 |
|    71 |      516 |    873 |

### Summary Statistics

#### Median Values (50th percentile)
- **Input**: 66 ms
- **Question**: 529 ms  
- **Answer**: 715 ms

#### Total Speech-to-Speech Conversion Lag
The total lag from releasing the push-to-talk button to hearing the response is **1.244 seconds** (Question + Answer medians). This measurement excludes the API response time, which is outside of Yova's boundaries.

## Design Strategies for Reducing Processing Lag Time

### 1. OpenAI Realtime API Integration

**Strategy**: Leverage OpenAI's realtime API capabilities for faster response generation.

**Benefits**:
- Reduced API round-trip time
- Lower latency for complex queries
- Better handling of long-form responses
- Improved streaming capabilities

### 2. Streaming Voice Transcription (Chunk by Chunk)

**Strategy**: Process audio input in real-time chunks rather than waiting for complete speech.

**Benefits**:
- Earlier detection of speech completion
- Reduced perceived latency
- Better handling of long utterances
- Improved accuracy through context accumulation

### 3. Streaming API/Backend Responses

**Strategy**: Stream responses from the backend API instead of waiting for complete responses.

**Benefits**:
- Faster start of text-to-speech processing
- Reduced time-to-first-audio
- Better user experience for long responses
- Improved perceived responsiveness

### 4. Chunked Text-to-Speech Processing

**Strategy**: Convert text to speech in sentence-sized chunks to start audio playback earlier.

**Benefits**:
- Reduced time-to-first-audio
- Better handling of long responses
- Improved perceived responsiveness
- More natural speech flow

## Pro Tips for Optimal Performance

### Pro Tip 1: Immediate Feedback Implementation

To make Yova feel even more responsive, implement **immediate feedback** right after the user finishes speaking:

#### How It Works
1. **User finishes speaking** → Yova detects speech completion
2. **Immediate response** → Play a quick acknowledgment sound/word
3. **Process request** → Continue with the normal API call flow

#### Implementation Options

##### Option 1: Text-to-Speech (Good)
- **Trigger**: Listen for `yova.asr.result` event (when speech recognition completes)
- **Response**: Immediately publish `yova.api.tts.chunk` with a quick acknowledgment
- **Examples**: "Hmm...", "Okay...", "Sure thing...", "Got it...", "Right..."
- **Latency**: ~200-400ms for acknowledgment + normal processing

##### Option 2: Pre-recorded Audio (Best - Lowest Latency)
- **Trigger**: Listen for `yova.asr.result` event
- **Response**: Publish `yova.api.tts.chunk` with base64-encoded audio
- **Format**: `data:audio/wav;base64,UklGRiQA...` (see events.md for details)
- **Examples**: Pre-record "Hmm...", "Okay...", "Sure thing..." as WAV files
- **Latency**: ~50-100ms (no TTS processing needed)

#### Benefits
- **Perceived responsiveness**: User gets instant feedback that Yova heard them
- **Better UX**: Eliminates the "did it hear me?" uncertainty
- **Natural conversation flow**: Mimics human conversation patterns
- **Lower latency**: Pre-recorded audio eliminates TTS processing time

### Pro Tip 2: Optimize Response Structure for Faster TTS

**Strategy**: Structure responses to start with short, simple sentences.

**Why It Works**:
- Short sentences are processed faster by TTS engines
- Simple sentence structures require less linguistic analysis
- Early audio playback improves perceived responsiveness
- Complex sentences can follow after the initial response

**Examples**:
- ✅ **Good**: "Sure! The capital of France is Paris. It's a beautiful city known for..."
- ❌ **Avoid**: "Well, let me think about that for a moment. The capital of France, which is located in Western Europe and has a rich history dating back to..."

**Implementation**:
- Instruct AI models to start responses with concise statements
- Use response templates that prioritize brevity early
- Implement response restructuring if needed
- Monitor TTS processing times for different sentence lengths