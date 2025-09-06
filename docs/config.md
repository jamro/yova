# Configuration

The Yova project uses a JSON configuration file to manage various settings for speech recognition, text-to-speech, and OpenAI integration.

## Configuration Files

- **`yova.config.json`** - Your active configuration file (should not be committed to version control)
- **`yova.config.default.json`** - Template configuration file with default values

## Configuration Structure

The configuration is organized into three main sections:

### OpenAI Configuration (`open_ai`)

```json
{
  "open_ai": {
    "api_key": "your-openai-api-key-here"
  }
}
```

**Parameters:**
- `api_key` (string, required): Your OpenAI API key for accessing speech and transcription services

### Text-to-Speech Configuration (`text2speech`)

```json
{
  "text2speech": {
    "model": "gpt-4o-mini-tts",
    "voice": "nova",
    "speed": 1.25,
    "instructions": "You are a English voice assistant. Read the input text aloud in natural, fluent language with clear pronunciation. Maintain a polite and helpful tone. Do not translate or improvise."
  }
}
```

**Parameters:**
- `model` (string): OpenAI TTS model to use (e.g. "gpt-4o-mini-tts")
- `voice` (string): Voice to use for speech synthesis
- `speed` (float): Speech playback speed multiplier
- `instructions` (string): Instructions for the AI voice personality and language

### Speech-to-Text Configuration (`speech2text`)

```json
{
  "speech2text": {
    "model": "gpt-4o-transcribe",
    "streaming": true,
    "instructions": "The audio is an English voice command for a voice assistant. Transcribe only if the speech is clear and logical. Use correct spelling and punctuation. If the audio is unclear, contains noise, or is not valid, return an empty string ''). Do not attempt to guess or translate.",
    "language": "en",
    "noise_reduction": "far_field",
    "audio_logs_path": "",
    "prerecord_beep": "beep7.wav",
    "preprocessing": {
      "min_speech_length": 0.5,
      "high_pass_cutoff_freq": 70.0,
      "declicking": true,
      "noise_supresion_level": 2,
      "agc_enabled": true,
      "vad_aggressiveness": 2,
      "normalization_enabled": true,
      "normalization_target_rms_dbfs": -20.0,
      "normalization_peak_limit_dbfs": -3.0,
      "edge_fade_enabled": true
    }
  }
}
```

**Parameters:**
- `model` (string): OpenAI transcription model to use (e.g. "gpt-4o-transcribe")
- `streaming` (boolean): Whether to use streaming transcription API. Streaming API is faster but less accurate.
- `instructions` (string): Instructions for the transcription model on how to process and format the audio input
- `language` (string): Language code for speech recognition (e.g., "en", "pl")
- `noise_reduction` (string): Noise reduction setting for audio processing (see [OpenAI API documentation](https://platform.openai.com/docs/guides/realtime-transcription#noise-reduction) for more details)
- `audio_logs_path` (string): Path to store audio logs; if set, all recorded commands will be saved to disk (empty string disables logging)
- `prerecord_beep` (string): Audio file to play before recording (from `yova_shared/assets/`)

**Preprocessing Parameters:**
- `min_speech_length` (float): Minimum length of speech to be transcribed (in seconds)
- `high_pass_cutoff_freq` (float): Cutoff frequency in Hz for high-pass filter
- `declicking` (boolean): Enable declicking to reduce audio artifacts
- `noise_supresion_level` (integer): Noise suppression level (0-3, higher = more aggressive)
- `agc_enabled` (boolean): Enable Automatic Gain Control
- `vad_aggressiveness` (integer): Voice Activity Detection aggressiveness (0-3, higher = more aggressive)
- `normalization_enabled` (boolean): Enable audio normalization
- `normalization_target_rms_dbfs` (float): Normalisation Target RMS level in dBFS for normalization
- `normalization_peak_limit_dbfs` (float): Normalisation Peak limit in dBFS to prevent clipping
- `edge_fade_enabled` (boolean): Enable edge fading to reduce audio artifacts

### Voice ID Configuration (`voice_id`)

```json
{
  "voice_id": {
    "enabled": false,
    "include_embedding": false,
    "threshold": 0.267
  }
}
```

**Parameters:**
- `enabled` (boolean): Whether to enable Voice ID
- `include_embedding` (boolean): Whether to include the embedding in the voice ID payload
- `threshold` (float): Similarity threshold for speaker verification (0.0 to 1.0)

More details in [Voice ID documentation](voice_id.md).

## Setup Instructions

1. **Copy the template:**
   ```bash
   cp yova.config.default.json yova.config.json
   ```

2. **Edit your configuration:**
   - Add your OpenAI API key
   - Customize language settings
   - Adjust audio processing parameters
   - Set audio logging path if desired

3. **Keep your config private:**
   - Never commit `yova.config.json` to version control
   - The `.gitignore` file should exclude this file

## Available Audio Assets

The following beep sounds are available in `yova_shared/assets/`:
- `beep1.wav` through `beep11.wav`
- `test_sound.wav`

## Audio Processing Tuning

### Noise Reduction
- `"far_field"`: Optimized for distant microphones
- Other options may be available depending on the OpenAI model

### Speech Detection
- Adjust `preprocessing.min_speech_length` based on your speaking style

### Audio Preprocessing
The preprocessing section contains advanced audio processing parameters:

- **High-Pass Filter**: `high_pass_cutoff_freq` removes frequencies below the cutoff
- **Declicking**: `declicking` reduces audio artifacts at segment boundaries
- **Noise Suppression**: `noise_supresion_level` (0-3) controls noise reduction aggressiveness
- **Automatic Gain Control**: `agc_enabled` automatically adjusts audio levels
- **Voice Activity Detection**: `vad_aggressiveness` (0-3) controls speech detection sensitivity
- **Normalization**: `normalization_enabled` with target RMS and peak limits for consistent audio levels
- **Edge Fading**: `edge_fade_enabled` reduces artifacts at audio segment edges

## Troubleshooting

### Common Issues
1. **API Key Errors**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Audio Quality**: Adjust noise reduction, threshold settings, and capture/playback volume for your environment. See [Troubleshooting Guide](troubleshooting.md) for more details.
3. **Language Mismatch**: Ensure the language setting matches your speech and instructions