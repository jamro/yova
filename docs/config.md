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
    "instructions": "Speak in a friendly, engaging tone. Always answer in Polish."
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
    "instructions": "The audio is a voice command for a voice assistant. Transcribe only if the speech is clear and logical. Use correct spelling and punctuation. If the audio is unclear, contains noise, or is not valid, return an empty string. Do not attempt to guess or translate.",
    "language": "pl",
    "noise_reduction": "far_field",
    "min_speech_length": 0.5,
    "silence_amplitude_threshold": 0.15,
    "audio_logs_path": "/path/to/audio/logs/",
    "prerecord_beep": "beep1.wav"
  }
}
```

**Parameters:**
- `model` (string): OpenAI transcription model to use (e.g. "gpt-4o-transcribe")
- `instructions` (string): Instructions for the transcription model on how to process and format the audio input
- `language` (string): Language code for speech recognition (e.g., "en", "pl")
- `noise_reduction` (string): Noise reduction setting for audio processing (see [OpenAI API documentation](https://platform.openai.com/docs/guides/realtime-transcription#noise-reduction) for more details)
- `min_speech_length` (float): Minimum length of speech segment in seconds
- `silence_amplitude_threshold` (float): Threshold for detecting silence
- `audio_logs_path` (string): Path to store audio logs; if set, all recorded commands will be saved to disk (empty string disables logging)
- `prerecord_beep` (string): Audio file to play before recording (from `yova_shared/assets/`)

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
- Adjust `min_speech_length` based on your speaking style
- Lower `silence_amplitude_threshold` values make the system more sensitive to quiet speech

## Troubleshooting

### Common Issues
1. **API Key Errors**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Audio Quality**: Adjust noise reduction, threshold settings, and capture/playback volume for your environment. See [Troubleshooting Guide](troubleshooting.md) for more details.
3. **Language Mismatch**: Ensure the language setting matches your speech and instructions