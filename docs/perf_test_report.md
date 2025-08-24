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

## Summary Statistics

### Median Values (50th percentile)
- **Input**: 66 ms
- **Question**: 529 ms  
- **Answer**: 715 ms

### Total Speech-to-Speech Conversion Lag
The total lag from releasing the push-to-talk button to hearing the response is **1.244 seconds** (Question + Answer medians). This measurement excludes the API response time, which is outside of Yova's boundaries.