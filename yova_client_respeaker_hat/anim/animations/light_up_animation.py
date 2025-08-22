#!/usr/bin/env python3
import math
from .base_animation import BaseAnimation

DARK = (0, 0, 0)

class LightUpAnimation(BaseAnimation):
    """Light up animation - light up the LEDs one by one."""
    
    def __init__(self, led_strip, color: tuple = (0, 0, 255), total_steps=120):
        super().__init__(led_strip)
        self.color = color
        self._current_step = 0
        self._total_steps = total_steps
    
    def _animate_frame(self) -> bool:
        """Animate one frame of light up animation."""
            
        progress = 4 * (self._current_step / self._total_steps)
        stage = int(progress)
        amplitude = (progress - stage)
        amplitude = math.sin(amplitude * math.pi * 0.5)

        colors = []
        
        if stage == 0:
            colors.append(
                (int(self.color[0] * amplitude), 
                int(self.color[1] * amplitude), 
                int(self.color[2] * amplitude)))
            colors.append(DARK)
            colors.append(DARK)
        elif stage == 1:
            colors.append(self.color)
            colors.append(
                (int(self.color[0] * amplitude), 
                int(self.color[1] * amplitude), 
                int(self.color[2] * amplitude)))
            colors.append(DARK)
        elif stage == 2:
            colors.append(self.color)
            colors.append(self.color)
            colors.append(
                (int(self.color[0] * amplitude), 
                int(self.color[1] * amplitude), 
                int(self.color[2] * amplitude)))
        elif stage == 3:
            fade_out = (
                int(self.color[0] * (1-amplitude)), 
                int(self.color[1] * (1-amplitude)), 
                int(self.color[2] * (1-amplitude))
            )
            colors.append(fade_out)
            colors.append(fade_out)
            colors.append(fade_out)
        
        self.set_lights(colors)

            
        # Update step for next frame
        self._current_step = self._current_step + 1
        
        return (self._current_step <= self._total_steps)
    
    def reset(self) -> None:
        """Reset animation to initial state."""
        super().reset()
        self._current_step = 0
