# AST Test Insights

- Realtime API is less accurate than non-realtime API (WER 55% vs 12%)
- Processing time for streaming can vary significanty (0.74ms - 1.41ms)
- There is a time processing gain when using realtime API (Processing Time 0.95ms for realtime vs 1.59ms for non-realtime)
- 4o-transcribe is slightlymore accurate than whisper-1 (Streaming WER 55% vs 66%, Non-Streaming WER 12% vs 14%)
- High pass filter improves accuracy for streaming (WER 55% vs 27%)
- Noise suppression seems to reduce accuracy for streaming (WER 27% to 33%)
- Difference between noise suppression levels 1, 2 and 3 is not significant
- VAD seems to not improve accuracy for streaming
- VAD aggressivness above 1 seems to reduce accuracy for streaming (WER 31% - 35% vs 27%)
- AGC seems to not impact accuracy for streaming significantly
- Normalization (target RMS -20dBFS, peak limit -3dBFS) improves accuracy for streaming slightly (WER 27% to 23%)
- Edge fade seems to reduce accuracy for streaming slightly or not impact it at all