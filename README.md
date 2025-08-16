# Voice Command Station

## Hardware

- [Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)
- [ReSpeaker 2-Mic HAT](https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html)
- [Mini Speaker 8Ohm, 1Watt](https://www.adafruit.com/product/4227?srsltid=AfmBOorOZtwiBuU8zXa5sDeZ4aSFk7Tloh-Bxvi2tBpuQOI0XpLW2rrd)
- JST PH2.00 Connector, 2 pins, 2.00mm pitch

## Raspberry Pi Configuration

Prepare Rasperry PI SD card with [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
- Rapberry Pi Device: Raspberry Pi 5
- Operating System: Raspberry Pi OS (64-bit)
- Configuration (Edit Settings)
  - General:
    - Set hostname: `voice.local`
    - Set username and password: **checked**
    - Set username: `pi`
    - Set password: `your password`
    - Configure Wireless LAN: **checked**
    - SSID: `your wifi network name`
    - Password: `your wifi network password`
  - Services:
    - Enable SSH: **checked**
    - Allow public-key authentication: **checked** (recommended)
    - Set authorized keys for `pi`: `your public key`


Connect to Raspberry Pi via SSH:
```bash
ssh pi@voice.local
```

Install ReSpeaker HAT drivers:
```bash
curl https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/refs/heads/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dts
dtc -I dts respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dtbo
sudo dtoverlay respeaker-2mic-v2_0-overlay.dtbo
sudo cp respeaker-2mic-v2_0-overlay.dtbo /boot/firmware/overlays
```

Edit `/boot/firmware/config.txt` and add the following lines under `[all]` section:
```
# ReSpeaker HAT
dtoverlay=respeaker-2mic-v2_0-overlay
dtoverlay=i2s-mmap
```

Reboot your Pi `sudo reboot`

The expected output for `aplay` should be:

```bash
pi@voice:~ $ aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: seeed2micvoicec [seeed2micvoicec], device 0: 1f000a4000.i2s-tlv320aic3x-hifi tlv320aic3x-hifi-0 [1f000a4000.i2s-tlv320aic3x-hifi tlv320aic3x-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

The expected output for `arecord` should be:

```bash
pi@voice:~ $ arecord -l
**** List of CAPTURE Hardware Devices ****
card 2: seeed2micvoicec [seeed2micvoicec], device 0: 1f000a4000.i2s-tlv320aic3x-hifi tlv320aic3x-hifi-0 [1f000a4000.i2s-tlv320aic3x-hifi tlv320aic3x-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```