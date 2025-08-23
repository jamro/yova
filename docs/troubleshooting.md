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

### Audio Device Detection

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
sudo systemctl status supervisord.service

# Check if service is enabled (starts on boot)
sudo systemctl is-enabled supervisord.service

# View service logs
sudo journalctl -u supervisord.service -f
```

### Restart YOVA Service
```bash
# Restart service (after configuration changes)
sudo systemctl restart supervisord.service

# Start service if stopped
sudo systemctl start supervisord.service

# Stop service
sudo systemctl stop supervisord.service
```