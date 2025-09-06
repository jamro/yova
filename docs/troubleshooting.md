# Troubleshooting

## Audio Issues

### ReSpeaker HAT Not Detected
If the ReSpeaker HAT is not detected as an audio device:

1. **Check hardware connections:**
   - Ensure the HAT is properly seated on the GPIO pins
   - Verify the HAT has its own power supply connected
   - Check that the case isn't putting pressure on the HAT

2. **Reboot required:**
   - After adding device tree overlays, a reboot is mandatory
   - Run: `sudo reboot`

### Audio Playback Issues

**Problem:** No sound or very quiet audio output

**Solution - Adjust Playback Volume:**
```bash
# Open alsamixer for volume adjustment
alsamixer
```

**Recommended Playback Settings:**
1. **Press F6** to select output device
2. **Select 'seeed2micvoicec'** from the device list
3. **Set PCM to 100%** (use arrow keys or mouse wheel)
4. **Set Line DAC to 100%** (use arrow keys or mouse wheel)
5. **Press ESC** to exit

### Audio Recording Issues

**Problem:** Microphone not working or recording too quiet/loud

**Solution - Adjust Recording Volume:**
```bash
# Open alsamixer for recording volume adjustment
alsamixer
```

**Recommended Recording Settings:**
1. **Press F6** to select input device
2. **Select 'seeed2micvoicec'** from the device list
3. **Press F4** to filter capture settings
4. **Set Capture (PGA) to 30%** (recommended - avoid going too high to prevent clipping)
5. **Press ESC** to exit

### Audio Device Detection and Voice Command Recognition

**Check available audio devices:**
```bash
# List playback devices
aplay -l

# List recording devices
arecord -l
```

**Expected output for ReSpeaker HAT:**
```
card 2: seeed2micvoicec [seeed2micvoicec], device 0: ...
```

**If device not found:**
1. Ensure you've rebooted after adding device tree overlays
2. Check `/boot/firmware/config.txt` contains:
   ```
   [all]
   # ReSpeaker HAT
   dtoverlay=respeaker-2mic-v2_0-overlay
   dtoverlay=i2s-mmap
   dtparam=spi=on
   ```

**Poor Voice Command Recognition:**

**Problem:** Voice commands are not being recognized accurately or consistently

**Symptoms:**
- Commands are misinterpreted or not understood
- System responds to unintended phrases
- Recognition works inconsistently
- Background noise interferes with command detection

**Troubleshooting Steps:**

1. **Adjust Audio Preprocessing Settings:**
   - Review and modify preprocessing parameters in your configuration file
   - Experiment with different noise reduction and gain settings
   - Fine-tune voice activity detection thresholds

   See [config.md](config.md) for more details.

2. **Enable Audio Logging for Analysis:**
   - Enable audio_logs_path in your configuration. This will record all voice commands for quality review
   - Review recorded audio files to assess command clarity
   - Check for background noise, speech volume, and pronunciation issues
   - Identify patterns in failed recognition attempts

   See [config.md](config.md) for more details.

3. **Use Development Tools for Recognition Analysis:**
   ```bash
   # Run development tools to analyze recognition patterns
   make dev-tools
   ```
   - Examine what phrases the system is actually recognizing
   - Compare expected vs. actual transcriptions
   - Identify common recognition errors and patterns

4. **Disable Speech2Text Streaming for Better Accuracy:**
   - If recognition accuracy is poor despite other adjustments, try disabling streaming mode
   - This will add approximately 500ms of latency but may significantly improve accuracy
   - In your configuration file, set `speech2text.streaming` to `false`:
   ```json
   "speech2text": {
     "streaming": false,
     ...
   }
   ```
   - Restart the Yova service after making this change:
   ```bash
   sudo systemctl restart yova.service
   ```

**Additional Recommendations:**
- Speak clearly and at a consistent volume
- Minimize background noise when giving commands
- Use consistent phrasing for voice commands
- Consider adjusting microphone sensitivity if commands are too quiet or loud
- Test recognition in different acoustic environments

### ALSA Configuration Issues

To ensure Yova runs correctly as a system service, you **must** configure ALSA with a global `/etc/asound.conf` file. This allows audio access for background services (not just your user session).

**Check current ALSA config:**
```bash
cat /etc/asound.conf
```

**Expected configuration:**
```
pcm.!default {
    type plug
    slave.pcm "hw:2,0"
    slave.rate 16000
}
ctl.!default {
    type hw
    card 2
}
```

**Note:** The card and device numbers (2,0) may vary. Use the numbers from `aplay -l` output.

### Audio Testing Commands

**Test playback:**
```bash
# Download test audio file
curl -L -o test_sound.wav https://github.com/jamro/yova/raw/refs/heads/main/yova_shared/assets/test_sound.wav

# Play test sound (replace X,Y with your card,device numbers)
aplay -D "plughw:2,0" test_sound.wav
```

**Test recording:**
```bash
# Record 5 seconds of audio
arecord -D "plughw:2,0" -f S16_LE -c1 -r 16000 -d 5 rec_test.wav

# Play back recorded audio
aplay -D "plughw:2,0" rec_test.wav
```

## Service Issues

### Check YOVA Service Status
```bash
# Check if service is running
sudo systemctl status yova.service

# Check if service is enabled (starts on boot)
sudo systemctl is-enabled yova.service

# View service logs
sudo journalctl -u yova.service -f
```

### Restart YOVA Service
```bash
# Restart service (after configuration changes)
sudo systemctl restart yova.service

# Start service if stopped
sudo systemctl start yova.service

# Stop service
sudo systemctl stop yova.service
```