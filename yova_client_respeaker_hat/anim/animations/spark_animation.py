#!/usr/bin/env python3
import math
import random
from .base_animation import BaseAnimation

DARK = (0, 0, 0)

DURATION_MIN = 60
DURATION_MAX = 80

class SparkAnimation(BaseAnimation):
    """Light up animation - light up the LEDs one by one."""
    
    def __init__(self, led_strip, color: tuple = (255, 255, 255)):
        super().__init__(led_strip)
        self.color = color
        self._current_step = 0
        self._total_steps = random.randint(DURATION_MIN, DURATION_MAX)
        self._led_index = random.randint(0, self.num_leds-1)
    
    def _animate_frame(self) -> bool:
        """Animate one frame of light up animation."""
            
        progress = (self._current_step / self._total_steps)
        amplitude = math.sin(progress * math.pi)

        colors = []
        for i in range(self.num_leds):
            if i == self._led_index:
                colors.append((
                    int(self.color[0] * amplitude), 
                    int(self.color[1] * amplitude), 
                    int(self.color[2] * amplitude)
                ))
            else:
                colors.append(DARK)
        
        self.set_lights(colors)

        # Update step for next frame
        self._current_step = self._current_step + 1
        
        return (self._current_step <= self._total_steps)
    
    def reset(self) -> None:
        """Reset animation to initial state."""
        super().reset()
        self._current_step = 0
        self._total_steps = random.randint(DURATION_MIN, DURATION_MAX)
        self._led_index = random.randint(0, self.num_leds-1)
