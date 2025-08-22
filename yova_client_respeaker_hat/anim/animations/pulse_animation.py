#!/usr/bin/env python3
import math
from .base_animation import BaseAnimation

class PulseAnimation(BaseAnimation):
    """Pulse animation - smooth brightness transitions for listening/recording states."""
    
    def __init__(self, led_strip, color: tuple = (0, 0, 255), min_brightness=0.05, max_brightness=1.0, total_steps=60):
        super().__init__(led_strip)
        self.color = color
        self._current_step = 0
        self._total_steps = total_steps
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
    
    def _animate_frame(self) -> bool:
        """Animate one frame of pulse animation."""
            
        # Calculate brightness using smooth sine wave
        progress = self._current_step / self._total_steps
        amplitude = (1 - math.cos(progress * 2 * math.pi)) / 2
        amplitude = (self.min_brightness + (self.max_brightness - self.min_brightness) * amplitude)
        
        # Create dynamic wave effect across LEDs
        colors = []
        for i in range(self.num_leds):
        
            # Create color with subtle variations for more interest
            r = int(self.color[0] * amplitude)
            g = int(self.color[1] * amplitude)
            b = int(self.color[2] * amplitude)
            
            colors.append((r, g, b))
        
        # Show the frame
        self.set_lights(colors)
        
        # Update step for next frame
        self._current_step = self._current_step + 1
        
        return (self._current_step <= self._total_steps)
    
    def reset(self) -> None:
        """Reset animation to initial state."""
        super().reset()
        self._current_step = 0
