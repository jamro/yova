# Performance Test Report

## Test Setup

- Test Device: Raspberry Pi 5
- Test Sentence: "What is the capital of France?"
- text2speech model: gpt-4o-mini-tts
- speech2text model: gpt-4o-transcribe

## Timing Definitions

Before presenting the test results, it's important to understand what each timing measurement represents:

- **Input**: Duration from pressing the push-to-talk button to the start of recording
- **Question**: Duration from releasing the push-to-talk button to sending the message to the backend API
- **Answer**: Duration from receiving the first chunk of response from the backend API to the start of playing speech

**Note**: All durations are measured in milliseconds (ms).

## Test Results:

| Input | Question | Answer |
|-------|----------|--------|
|   721 |      487 |    695 |
|   378 |      501 |    582 |
|   392 |      546 |    581 |
|   375 |      521 |    459 |
|   442 |      526 |    715 |
|   421 |      603 |    740 |
|   416 |      830 |   1042 |
|   415 |      552 |    573 |
|   407 |      529 |    951 |
|   421 |      634 |    797 |
|   444 |      516 |    873 |

## Summary Statistics

### Median Values (50th percentile)
- **Input**: 416 ms
- **Question**: 529 ms  
- **Answer**: 715 ms

### Total Speech-to-Speech Conversion Lag
The total lag from releasing the push-to-talk button to hearing the response is **1.244 seconds** (Question + Answer medians). This measurement excludes the API response time, which is outside of Yova's boundaries.