#!/usr/bin/env python3
import spidev
import atexit

NUM_LEDS = 3            # you have 3 LEDs
SPI_BUS = 0             # usually 0 on RPi
SPI_DEVICE = 0          # usually 0 (spidev0.0)
SPI_MAX_HZ = 2000000    # 2 MHz is completely sufficient (APA102 can handle more)

# APA102: start frame (4x 0x00), then for each LED: 0b111xxxxx + B, G, R
# brightness: 0..31 (5 bits), 31 = maximum
def _led_frame(r, g, b, brightness=31):
    brightness = max(0, min(31, brightness))
    return [0b11100000 | brightness, b & 0xFF, g & 0xFF, r & 0xFF]  # Note: BGR!

def _end_frame_bytes(n):
    # Required >= (n/2) bytes with ones, safely:
    return [0xFF] * ((n // 2) + 1)

class APA102:
    def __init__(self, num_leds=NUM_LEDS, bus=SPI_BUS, device=SPI_DEVICE, max_hz=SPI_MAX_HZ):
        self.num_leds = num_leds
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = max_hz
        self.spi.mode = 0b00
        self._closed = False
        atexit.register(self._cleanup)

    def show(self, colors, brightness=1.0):
        """
        colors: list [(r,g,b), ...] length num_leds
        brightness: 0.0..1.0 (global brightness)
        """
        if self._closed:
            return
            
        # Trim/pad to the number of LEDs
        colors = (colors[:self.num_leds] + [(0,0,0)] * self.num_leds)[:self.num_leds]
        
        # Reverse the order of colors to fix LED addressing
        colors = colors[::-1]

        start = [0x00, 0x00, 0x00, 0x00]
        frames = []
        for c in colors:
            if len(c) == 3:
                r, g, b = c
                frames += _led_frame(r, g, b, int(brightness * 31))
            else:
                # allows tuple (r,g,b,br)
                r, g, b, br = c
                frames += _led_frame(r, g, b, br)

        end = _end_frame_bytes(self.num_leds)
        try:
            self.spi.xfer2(start + frames + end)
        except (OSError, IOError) as e:
            # If SPI communication fails, mark as closed
            self._closed = True
            raise

    def off(self):
        """Turn off all LEDs"""
        if not self._closed:
            try:
                self.show([(0,0,0)] * self.num_leds, brightness=0.0)
            except Exception:
                pass  # Ignore errors when turning off

    def _cleanup(self):
        """Safe cleanup method for atexit"""
        if not self._closed:
            try:
                self.off()
            except Exception:
                pass  # Ignore all errors during cleanup
            finally:
                try:
                    if hasattr(self.spi, 'close'):
                        self.spi.close()
                except Exception:
                    pass  # Ignore errors when closing SPI
                self._closed = True

    def close(self):
        """Explicitly close the LED strip"""
        if not self._closed:
            self._cleanup()
