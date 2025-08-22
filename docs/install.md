# Installation

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

Install dependencies:
```bash
sudo apt update
sudo apt install -y build-essential python3-dev libasound2-dev libportaudio2 portaudio19-dev libportaudiocpp0 libjack-jackd2-dev python3-rpi-lgpio
sudo usermod -aG gpio pi
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

Adjust the volume by running `alsamixer`
- Adjust master playback volume (recommended to set to 80%)
- Press F4 and adjust capture volume (recommended to set to 80%)
- Press F6 to enter the menu and select output device `seeed2micvoiceec`. 
- Next press F4 to go to capure settings. Set everything to zero except PGA which sould be on (recommended to set to 25%)

Press Ctrl+C to exit the menu. Run `sudo alsactl store` to save the volume settings.

Manualy test the audio output and input. If you are not satisfied with the volume, you can adjust it again.

```bash
arecord -D plughw:2,0 -f S16_LE -c1 -r 16000 -d 5 test.wav
aplay -D plughw:2,0 test.wav
```

If you want to test the audio on your local machine copy the test.wav file:
```bash
scp pi@voice.local:/home/pi/test.wav ~/
```


Tell PortAudio exactly which ALSA device to use 

```bash
aplay -l
```

Example output: `card 2: seeed2micvoicec [seeed2micvoicec], device 0: ...`
Here:
	-	Card = 2 (seeed2micvoicec)
	-	Device = 0

Create `/etc/asound.conf` file:

```
pcm.!default {
    type plug
    slave.pcm "hw:2,0"     # adjust to your card,device
    slave.rate 16000       
}
ctl.!default {
    type hw
    card 2                 # same card number as above
}
```

Reboot the Raspberry Pi `sudo reboot`


Enable SPI (required for the ReSpeaker HAT LED)
```bash
sudo raspi-config
```
- Select `Interfacing Options`
- Select `SPI`
- Select `Yes`

## Software

```bash
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="/home/pi/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
source ~/.bashrc
git clone https://github.com/jamro/yova.git
cd yova
poetry config keyring.enabled false
make install
echo "OPENAI_API_KEY=..." > .env
cp yova.config.default.json yova.config.json
```

Edit `yova.config.json` and add your OpenAI API key.

```bash
sudo cp /home/pi/yova/scripts/supervisord.service /etc/systemd/system/supervisord.service
sudo systemctl daemon-reload
sudo systemctl enable supervisord.service
sudo systemctl start supervisord.service

sudo systemctl status supervisord.service
sudo journalctl -u supervisord.service -f
```
