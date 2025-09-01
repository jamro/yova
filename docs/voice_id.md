## Voice ID (short guide)

### What it is
- **Purpose**: Lightweight speaker identification for personalization and routing.
- **Model**: ECAPA-based speaker embeddings + similarity matching.
- **Output**: `user_id`, `similarity` (0–1), `confidence_level` (`high`/`medium`/`low`).
- **Scope**: Not strong authentication. Treat as a contextual signal.

### How it works
1. **Enrollment**: Record a few seconds of clean speech per user to create a voice profile.
2. **Embedding**: Each audio sample is converted to a speaker embedding (16 kHz, mono).
3. **Identification**: New audio is embedded and compared to enrolled profiles.
4. **Result**: Best match with similarity score and confidence.

### Enable in config
Add to your `yova.config.json` (see `docs/config.md`):
```json
{
  "voice_id": {
    "enabled": true,
    "include_embedding": false
  }
}
```
- **enabled**: Turns Voice ID on/off.
- **include_embedding**: If true, adds a large embedding payload to events.

### Where results appear
When enabled, ASR results include a `voice_id` block in `yova.api.asr.result` events (see `docs/events.md`).

### Enrollment tips
- **Amount**: 2–5 seconds per sample; 2–3 samples per user help robustness.
- **Quality**: Quiet room, consistent mic distance.
- **Consistency**: Use the same device/setup as typical usage if possible.
- **Language**: It doesn't matter. ECAPA is text‑independent—any language/content works. Speak naturally (avoid whispering/shouting).

### Storage location
- Default profiles path: `yova_core/.data/voice_id/users`
- Profiles persist between runs and are auto-loaded at startup.

### Quick enrollment
- Run the built-in CLI:
```bash
make voice-id
```
- Follow the on-screen prompts to enroll users and test identification.

### Limitations & notes
- Voice ID adds small latency but runs in parallel with ASR.
- Use for personalization, not permissions or security-sensitive actions.
- Similarity/confidence depend on mic, environment, and enrollment quality.


### Advanced solutions
- You can build richer pipelines on top of raw embeddings:
  - **Automatic clustering**: Group voices with K-Means/HDBSCAN to discover users, then label clusters when confirmed.
  - **Incremental learning**: Accumulate embeddings per user to improve robustness over time and devices.
  - **Active confirmation**: For low-confidence matches, ask the user to confirm and update the profile.
  - **Context-aware profiles**: Maintain multiple sub-profiles per device/room/mic and merge at query time.
- To consume raw embeddings in real-time, set `voice_id.include_embedding: true` and subscribe to `yova.api.asr.result`. See `[docs/events.md](events.md)` for the embedding payload format.


